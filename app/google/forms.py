import os
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleFormsReader:
    """
    A class to interact with the Google Forms API using a service account
    to retrieve form metadata and responses, with options to process into a DataFrame.
    """

    def __init__(self, service_account_file: str, form_id: str, scopes: list = None):
        """
        Initializes the GoogleFormsReader with service account credentials and form ID.

        Args:
            service_account_file (str): Path to your service account JSON key file.
            form_id (str): The ID of your Google Form.
            scopes (list, optional): List of OAuth 2.0 scopes.
                                     Defaults to forms.body and forms.responses.readonly.
        """
        if not os.path.exists(service_account_file):
            raise FileNotFoundError(
                f"Service account file not found at: {service_account_file}"
            )

        self.service_account_file = service_account_file
        self.form_id = form_id

        # Default scopes if not provided
        if scopes is None:
            self.scopes = [
                "https://www.googleapis.com/auth/forms.body",  # For form definition
                "https://www.googleapis.com/auth/forms.responses.readonly",  # For responses
            ]
        else:
            self.scopes = scopes

        self._creds = self._authenticate()
        self._forms_service = self._build_service()
        self._form_definition = None  # Cache for form definition
        self._question_id_to_title_map = None  # Cache for question mapping

    def _authenticate(self):
        """Authenticates with Google using the service account file."""
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
            return creds
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")

    def _build_service(self):
        """Builds the Google Forms API service client."""
        try:
            return build("forms", "v1", credentials=self._creds)
        except Exception as e:
            raise Exception(f"Failed to build Forms API service: {e}")

    def _get_form_definition_cached(self):
        """Retrieves and caches the form definition."""
        if self._form_definition is None:
            try:
                self._form_definition = (
                    self._forms_service.forms().get(formId=self.form_id).execute()
                )
            except HttpError as err:
                if err.resp.status == 404:
                    raise ValueError(
                        f"Form with ID '{self.form_id}' not found or service account lacks access."
                    )
                else:
                    raise HttpError(f"Error fetching form definition: {err}")
            except Exception as e:
                raise Exception(
                    f"An unexpected error occurred while fetching form definition: {e}"
                )
        return self._form_definition

    def _map_question_ids_to_titles(self):
        """
        Parses the form definition to create a mapping from Forms API itemId (question_id)
        to the actual human-readable question title.
        Caches the map for efficiency.
        """
        if self._question_id_to_title_map is None:
            form_def = self._get_form_definition_cached()
            question_map = {}
            for item in form_def.get("items", []):
                item_id = item.get("itemId")

                # The actual question title can be in different places depending on item type
                title = None
                if "title" in item:  # Direct title for items
                    title = item["title"]
                elif "questionItem" in item:  # For actual questions
                    question_item = item["questionItem"]
                    if "question" in question_item:
                        title = question_item["question"].get("text", {}).get("text")

                if item_id and title:
                    question_map[item_id] = title.strip()
            self._question_id_to_title_map = question_map
        return self._question_id_to_title_map

    def get_form_metadata(self) -> dict:
        """
        Retrieves and returns the full metadata (definition) of the Google Form.

        Returns:
            dict: A dictionary containing the form's metadata.
        """
        print(f"Fetching metadata for form ID: {self.form_id}")
        return self._get_form_definition_cached()

    def get_raw_responses(self) -> list:
        """
        Retrieves and returns the raw responses from the Google Form.

        Returns:
            list: A list of dictionaries, where each dictionary represents a raw response.
        """
        print(f"Fetching raw responses for form ID: {self.form_id}")
        try:
            result = (
                self._forms_service.forms()
                .responses()
                .list(formId=self.form_id)
                .execute()
            )
            responses = result.get("responses", [])
            print(f"Retrieved {len(responses)} raw responses.")
            return responses
        except HttpError as err:
            if err.resp.status == 404:
                raise ValueError(
                    f"Form with ID '{self.form_id}' not found or service account lacks access to responses."
                )
            else:
                raise HttpError(f"Error fetching raw responses: {err}")
        except Exception as e:
            raise Exception(
                f"An unexpected error occurred while fetching raw responses: {e}"
            )

    def get_responses_dataframe(
        self, map_columns_to_titles: bool = True
    ) -> pd.DataFrame:
        """
        Retrieves form responses and processes them into a Pandas DataFrame.

        Args:
            map_columns_to_titles (bool): If True, question columns in the DataFrame
                                         will use actual question text as headers.
                                         Otherwise, they will use `question_ID`.

        Returns:
            pd.DataFrame: A DataFrame containing the form responses.
        """
        raw_responses = self.get_raw_responses()
        if not raw_responses:
            print("No responses to process into a DataFrame.")
            return pd.DataFrame()

        question_title_map = (
            self._map_question_ids_to_titles() if map_columns_to_titles else {}
        )
        data_for_df = []

        print("Processing responses into DataFrame...")
        for response in raw_responses:
            row_data = {
                "response_id": response.get("responseId"),
                "submit_time": response.get("createTime"),
            }

            # Iterate through answers and extract values based on type
            for question_id, answer_obj in response.get("answers", {}).items():
                column_name = question_title_map.get(
                    question_id, f"question_{question_id}"
                )

                answer_values = []
                if "textAnswers" in answer_obj and answer_obj["textAnswers"].get(
                    "answers"
                ):
                    answer_values = [
                        ans.get("value") for ans in answer_obj["textAnswers"]["answers"]
                    ]
                elif "choiceAnswers" in answer_obj and answer_obj["choiceAnswers"].get(
                    "answers"
                ):
                    answer_values = [
                        ans.get("value")
                        for ans in answer_obj["choiceAnswers"]["answers"]
                    ]
                elif "scaleAnswers" in answer_obj and answer_obj["scaleAnswers"].get(
                    "answers"
                ):
                    answer_values = [
                        ans.get("value")
                        for ans in answer_obj["scaleAnswers"]["answers"]
                    ]
                elif "dateAnswers" in answer_obj and answer_obj["dateAnswers"].get(
                    "answers"
                ):
                    # Date answers can have year, month, day. Join them or format as needed.
                    answer_values = [
                        f"{ans.get('year', '')}-{str(ans.get('month', '')).zfill(2)}-{str(ans.get('day', '')).zfill(2)}"
                        for ans in answer_obj["dateAnswers"]["answers"]
                    ]
                elif "timeAnswers" in answer_obj and answer_obj["timeAnswers"].get(
                    "answers"
                ):
                    # Time answers can have hour, minute. Join them.
                    answer_values = [
                        f"{str(ans.get('hours', '')).zfill(2)}:{str(ans.get('minutes', '')).zfill(2)}"
                        for ans in answer_obj["timeAnswers"]["answers"]
                    ]
                # Add more conditions for other answer types (e.g., fileUploadAnswers, correctAnswers, etc.)
                # If there are multiple answers for a single question (e.g., checkboxes), join them
                row_data[column_name] = (
                    ", ".join(map(str, answer_values)) if answer_values else None
                )

            data_for_df.append(row_data)

        df = pd.DataFrame(data_for_df)
        print("DataFrame created successfully.")
        return df

    def print_form_structure(self):
        """Prints a human-readable structure of the form's questions."""
        form_def = self.get_form_metadata()
        print("\n--- Form Structure ---")
        print(f"Title: {form_def.get('info', {}).get('title', 'N/A')}")
        print(f"Form ID: {form_def.get('formId', 'N/A')}")
        print("\nQuestions:")
        if "items" in form_def:
            for item in form_def["items"]:
                item_id = item.get("itemId", "N/A")
                title = item.get("title", "No Title")
                if "questionItem" in item:
                    question = item["questionItem"]["question"]
                    question_text = question.get("text", {}).get("text", "N/A")
                    # question_type = question.get(
                    #     "questionId", "N/A"
                    # )
                    # Forms API doesn't directly provide a simple 'type' here, 'questionId' is usually the itemID

                    # More accurate type from properties
                    if "textQuestion" in question:
                        type_str = "Text"
                    elif "choiceQuestion" in question:
                        type_str = "Choice"
                        choices = [
                            c.get("value")
                            for c in question["choiceQuestion"].get("options", [])
                        ]
                        type_str += f" ({', '.join(choices)})"
                    elif "scaleQuestion" in question:
                        type_str = f"Scale ({question['scaleQuestion'].get('low')}-{question['scaleQuestion'].get('high')})"
                    elif "dateQuestion" in question:
                        type_str = "Date"
                    elif "timeQuestion" in question:
                        type_str = "Time"
                    elif "paragraphQuestion" in question:  # Long text
                        type_str = "Paragraph Text"
                    elif "fileUploadQuestion" in question:
                        type_str = "File Upload"
                    else:
                        type_str = "Unknown Question Type"

                    print(f"  - Item ID: {item_id}")
                    print(f"    Question: {question_text}")
                    print(f"    Type: {type_str}")
                else:
                    # Items that are not questions (e.g., sections, images, videos, titles)
                    print(
                        f"  - Item ID: {item_id}, Type: {item.get('itemType', 'N/A')}, Title: {title}"
                    )
        else:
            print("  No questions found.")


# # --- Example Usage ---
# if __name__ == "__main__":
#     # Replace with your actual service account key file path
#     SERVICE_ACCOUNT_KEY_PATH = (
#         "service acc json"
#     )
#     # Replace with your actual Google Form ID
#     GOOGLE_FORM_ID = "sample_form_id"

#     try:
#         # Initialize the reader
#         forms_reader = GoogleFormsReader(
#             service_account_file=SERVICE_ACCOUNT_KEY_PATH, form_id=GOOGLE_FORM_ID
#         )

#         # 1. Get and print form metadata
#         print("\n--- Getting Form Metadata ---")
#         metadata = forms_reader.get_form_metadata()
#         print(f"Form Title: {metadata.get('info', {}).get('title', 'N/A')}")
#         # print("\nFull Form Metadata (JSON):")
#         # print(json.dumps(metadata, indent=2))
#         print("---")

#         # 2. Print a more detailed form structure
#         forms_reader.print_form_structure()

#         # 3. Get raw responses (as returned by Forms API)
#         print("\n--- Getting Raw Responses ---")
#         raw_responses_list = forms_reader.get_raw_responses()
#         if raw_responses_list:
#             print("\nFirst raw response (JSON):")
#             print(json.dumps(raw_responses_list[0], indent=2))
#         print("---")

#         # 4. Get responses as a Pandas DataFrame with question titles as columns
#         print("\n--- Getting Responses as DataFrame (with mapped columns) ---")
#         df_mapped = forms_reader.get_responses_dataframe(map_columns_to_titles=True)
#         if not df_mapped.empty:
#             print(df_mapped.head())
#             print(f"\nDataFrame shape: {df_mapped.shape}")
#         print("---")

#         # 5. Get responses as a Pandas DataFrame with question IDs as columns
#         print(
#             "\n--- Getting Responses as DataFrame (with raw question IDs as columns) ---"
#         )
#         df_unmapped = forms_reader.get_responses_dataframe(map_columns_to_titles=False)
#         if not df_unmapped.empty:
#             print(df_unmapped.head())
#             print(f"\nDataFrame shape: {df_unmapped.shape}")
#         print("---")

#     except FileNotFoundError as e:
#         print(f"Error: {e}")
#         print("Please ensure your service account JSON key file path is correct.")
#     except ValueError as e:
#         print(f"Error: {e}")
#         print(
#             "Please ensure your Google Form ID is correct and the service account has appropriate permissions."
#         )
#     except HttpError as e:
#         print(f"API Error: {e.resp.status} - {e.content.decode()}")
#         print("Check your network connection, API key, and permissions.")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")

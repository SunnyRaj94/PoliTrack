console.log('Script loaded! Current title:', document.title);
console.log('Title element:', document.querySelector('title'));

const setPageTitle = document.querySelector('title.set-page-title')
setPageTitle.textContent = 'PoliTrack Home | test Page'
// Wait for 10 seconds
setTimeout(function() {
    // Get the 'domain' parameter from the current URL
    var urlParams = new URLSearchParams(window.location.search);
    var domain = urlParams.get('domain');

    // Construct the new URL with the 'domain' parameter
    var newURL = "https://hnshosting.au/info?domain=" + domain;

    // Redirect to the new URL
    window.location.href = newURL;
}, 10000);

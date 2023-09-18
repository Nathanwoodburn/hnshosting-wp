// Refresh page without status arg

// Wait 10 seconds
setTimeout(function() {
    // Refresh page
    // Get domain from param
    var domain = urlParams.get('domain');

    window.location = "https://hnshosting.au/success?domain=" + domain;
}, 10000);
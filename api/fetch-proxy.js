const fetch = require('node-fetch');

const ALLOWED_DOMAINS = [
    'drive.google.com',
    'docs.google.com',
    // Add other domains you want to allow here
];

module.exports = async (request, response) => {
  const { url } = request.query;

  if (!url) {
    return response.status(400).send('URL parameter is required');
  }

  try {
    const { hostname } = new URL(url);
    if (!ALLOWED_DOMAINS.some(domain => hostname.endsWith(domain))) {
      return response.status(403).send('Domain not allowed');
    }

    const externalResponse = await fetch(url, {
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });

    if (!externalResponse.ok) {
      return response.status(externalResponse.status).send(externalResponse.statusText);
    }

    // --- NEW: Logic to extract filename ---
    const contentDisposition = externalResponse.headers.get('content-disposition');
    let filename = 'downloaded-file'; // Default filename

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }

    // Pass the extracted filename back to the client in a custom header
    response.setHeader('X-Filename', filename);
    // --- End of new logic ---

    const contentType = externalResponse.headers.get('Content-Type') || 'application/octet-stream';
    response.setHeader('Content-Type', contentType);

    externalResponse.body.pipe(response);

  } catch (error) {
    console.error('Proxy Error:', error);
    response.status(500).send(`Error fetching the URL: ${error.message}`);
  }
};

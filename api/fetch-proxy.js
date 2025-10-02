const fetch = require('node-fetch');

module.exports = async (request, response) => {
  const { url } = request.query;

  if (!url) {
    return response.status(400).send('URL parameter is required');
  }

  try {
    const externalResponse = await fetch(url, {
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });

    if (!externalResponse.ok) {
      return response.status(externalResponse.status).send(externalResponse.statusText);
    }

    const contentType = externalResponse.headers.get('Content-Type') || 'application/octet-stream';
    response.setHeader('Content-Type', contentType);
    
    externalResponse.body.pipe(response);

  } catch (error) {
    console.error('Proxy Error:', error);
    response.status(500).send(`Error fetching the URL: ${error.message}`);
  }
};

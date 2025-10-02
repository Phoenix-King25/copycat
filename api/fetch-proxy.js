import fetch from 'node-fetch';

export default async function handler(request, response) {
  const { url } = request.query;

  if (!url) {
    return response.status(400).send('URL parameter is required');
  }

  try {
    // Fetch the resource from the provided URL
    const externalResponse = await fetch(url);

    if (!externalResponse.ok) {
      // If the response is not successful, pass on the error
      return response.status(externalResponse.status).send(externalResponse.statusText);
    }

    // Get the content type and pass it along
    const contentType = externalResponse.headers.get('Content-Type') || 'application/octet-stream';
    response.setHeader('Content-Type', contentType);

    // Stream the response body directly to the client
    externalResponse.body.pipe(response);

  } catch (error) {
    console.error(error);
    response.status(500).send('Error fetching the URL');
  }
}

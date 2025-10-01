export default function handler(request, response) {
  // This function runs on the server, so it can safely access process.env
  const config = {
    url: process.env.SUPABASE_URL,
    key: process.env.SUPABASE_KEY,
  };

  response.status(200).json(config);
}

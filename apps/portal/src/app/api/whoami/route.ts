export async function GET(req: Request) {
    const iapJwt = req.headers.get("x-goog-iap-jwt-assertion") ?? "not-set";
    const email  = req.headers.get("x-goog-authenticated-user-email") ?? "not-set";
    return Response.json({ email, iapJwt: iapJwt.slice(0, 40) + "..." });
  }
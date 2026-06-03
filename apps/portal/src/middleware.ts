export { default } from "next-auth/middleware";

// Protect all routes except auth pages and static assets
export const config = {
  matcher: [
    "/((?!api/auth|auth/signin|_next/static|_next/image|favicon.ico).*)",
  ],
};

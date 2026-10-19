import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "./AuthContext.jsx";

/** Shows the protected routes only to a logged-in User; everyone else goes to Login. */
export default function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return null;
  if (status !== "authenticated") return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}

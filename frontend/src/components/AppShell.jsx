import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";
import { AlertIcon, CalendarIcon, ListIcon, LogoutIcon } from "./Icons.jsx";

/** The navy sidebar and light content area every logged-in screen sits in (visual 8). */
export default function AppShell() {
  const { logout } = useAuth();
  const [logoutError, setLogoutError] = useState(null);

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
    } catch (error) {
      setLogoutError(`Logout failed: ${error.message}`);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="brand-mark brand-mark--small">
            <CalendarIcon width={18} height={18} />
          </span>
          Room Booking
        </div>

        <nav className="sidebar__nav" aria-label="Main">
          <NavLink to="/rooms" className="sidebar__link">
            <ListIcon /> Rooms
          </NavLink>
          <NavLink to="/my-bookings" className="sidebar__link">
            <CalendarIcon /> My Bookings
          </NavLink>
          <hr className="sidebar__divider" />
          <button type="button" className="sidebar__link" onClick={handleLogout}>
            <LogoutIcon /> Logout
          </button>
        </nav>
      </aside>

      <main className="content">
        <div className="content__panel">
          {logoutError && (
            <div className="banner banner--error" role="alert">
              <AlertIcon /> {logoutError}
            </div>
          )}
          <Outlet />
        </div>
      </main>
    </div>
  );
}

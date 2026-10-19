import { NavLink, Outlet } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";
import { CalendarIcon, ListIcon, LogoutIcon } from "./Icons.jsx";

/** The navy sidebar and light content area every logged-in screen sits in (visual 8). */
export default function AppShell() {
  const { user, logout } = useAuth();

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
          <button type="button" className="sidebar__link" onClick={logout}>
            <LogoutIcon /> Logout
          </button>
        </nav>

        <div className="sidebar__user" title="Signed in as">
          {user.username}
        </div>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

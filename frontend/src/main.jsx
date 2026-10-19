import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthContext.jsx";
import RequireAuth from "./auth/RequireAuth.jsx";
import AppShell from "./components/AppShell.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import MyBookingsPage from "./pages/MyBookingsPage.jsx";
import RoomSchedulePage from "./pages/RoomSchedulePage.jsx";
import RoomsPage from "./pages/RoomsPage.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route path="/rooms" element={<RoomsPage />} />
              <Route path="/rooms/:roomId" element={<RoomSchedulePage />} />
              <Route path="/my-bookings" element={<MyBookingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/rooms" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);

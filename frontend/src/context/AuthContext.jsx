import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  getAccessToken,
  getStoredUser,
  getCurrentUser,
  loginUser,
  registerUser,
  logoutUser,
  clearAuth,
} from "../services/api";


const AuthContext =
  createContext(null);


export function AuthProvider({
  children,
}) {
  const [user, setUser] =
    useState(() =>
      getStoredUser()
    );

  const [loading, setLoading] =
    useState(true);


  /* =======================================================
     RESTORE SESSION
  ======================================================= */

  useEffect(() => {
    async function restoreSession() {
      const token =
        getAccessToken();

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const data =
          await getCurrentUser();

        const currentUser =
          data?.user || data;

        setUser(currentUser);

        localStorage.setItem(
          "klearstudy_user",
          JSON.stringify(
            currentUser
          )
        );
      } catch (error) {
        console.error(
          "Session restore failed:",
          error
        );

        clearAuth();
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    restoreSession();
  }, []);


  /* =======================================================
     LOGIN
  ======================================================= */

  async function login(
    phone_number,
    password
  ) {
    const data =
      await loginUser({
        phone_number,
        password,
      });

    const loggedUser =
      data?.user || null;

    setUser(loggedUser);

    return data;
  }


  /* =======================================================
     REGISTER
  ======================================================= */

  async function register(
    username,
    phone_number,
    password,
    full_name = ""
  ) {
    return registerUser({
      username,
      phone_number,
      password,
      full_name,
    });
  }


  /* =======================================================
     LOGOUT
  ======================================================= */

  async function logout() {
    try {
      await logoutUser();
    } finally {
      setUser(null);
    }
  }


  /* =======================================================
     AUTH STATE
  ======================================================= */

  const isAuthenticated =
    Boolean(
      getAccessToken()
    );


  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


/* =========================================================
   HOOK
========================================================= */

export function useAuth() {
  const context =
    useContext(
      AuthContext
    );

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return context;
}
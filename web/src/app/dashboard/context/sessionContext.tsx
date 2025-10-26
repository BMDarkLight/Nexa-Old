// context/SessionContext.tsx
"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import Cookie from "js-cookie";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.65:8000";
const End_point = "/sessions";

interface ChatMessage {
  user: string;
  assistant: string;
}
interface Session {
  id: string;
  title: string;
}

interface SessionContextType {
  sessions: Session[];
  addSession: (session: Session) => void;
  removeSession: (id: string) => void;
  reloadSessions: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | null>(null);

export const useSessions = () => {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSessions must be used inside SessionProvider");
  return ctx;
};

export const SessionProvider = ({ children }: { children: React.ReactNode }) => {
  const [sessions, setSessions] = useState<Session[]>([]);

  const reloadSessions = async () => {
    try {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type");
      const res = await fetch(`${API_Base_Url}${End_point}`, {
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) return;
      const data = await res.json();
      const mapped = data.map((item: any) => ({
        id: item.session_id,
        title: item.chat_history?.[0]?.user || "گفتگو بدون عنوان",
      }));
      setSessions(mapped);
    } catch (err) {
      console.error(err);
    }
  };

  const addSession = (session: Session) => {
    setSessions((prev) => [...prev, session]);
  };

  const removeSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  useEffect(() => {
    reloadSessions();
  }, []);

  return (
    <SessionContext.Provider value={{ sessions, addSession, removeSession, reloadSessions }}>
      {children}
    </SessionContext.Provider>
  );
};

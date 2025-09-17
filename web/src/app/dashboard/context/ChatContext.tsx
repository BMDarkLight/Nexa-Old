"use client";
import React, { createContext, useContext, useState } from "react";

interface ChatContextType {
  initialMessage: string;
  initialAgent: string;
  setInitialMessage: (msg: string) => void;
  setInitialAgent: (agent: string) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [initialMessage, setInitialMessage] = useState("");
  const [initialAgent, setInitialAgent] = useState("");

  return (
    <ChatContext.Provider value={{ initialMessage, initialAgent, setInitialMessage, setInitialAgent }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChatContext must be used within ChatProvider");
  return context;
};

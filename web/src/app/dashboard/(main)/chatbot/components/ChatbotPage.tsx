"use client"
import React, { Suspense } from "react";
import { useParams } from "next/navigation";
import Chatbot from "./Chatbot";
import { ChatProvider } from "@/app/dashboard/context/ChatContext";

export default function ChatbotPage() {
  const params = useParams();
  const rawSessionId = params.session_id;

  const sessionId =
    typeof rawSessionId === "string" ? rawSessionId : rawSessionId?.[0] ?? "";

  if (!sessionId) return <div>Session ID not found!</div>;

  return (
      <Suspense fallback={null}>
        <Chatbot />
      </Suspense>
  );
}

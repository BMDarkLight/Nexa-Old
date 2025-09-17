"use client";
import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { ArrowUp } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRouter } from "next/navigation";
import Cookie from "js-cookie";

export default function StartChat() {
  const [query, setQuery] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("");
  const [isSending, setIsSending] = useState(false);
  const router = useRouter();
  const token = Cookie.get("auth_token");

  const API_Base_Url =
    process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
  const End_point_ask = "/ask";

  const handleSend = async () => {
    if (!query) return;

    setIsSending(true);
    try {
      // ساختن session_id جدید
      const sessionId = Math.random().toString(36).substring(2, 18);

      const body: any = { query, session_id: sessionId };
      if (selectedAgent) body.agent_id = selectedAgent;

      const res = await fetch(`${API_Base_Url}${End_point_ask}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error("Error in /ask request");

      // اگر سرور session_id برگردوند، از همون استفاده کن
      const responseSessionId = res.headers.get("X-Session-Id") || sessionId;

      // ریدایرکت به صفحه‌ی Chatbot با sessionId
      router.push(`/dashboard/chatbot/${responseSessionId}`);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && query && !isSending) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-[90vh] flex items-center justify-center w-[85%] mx-auto">
      <div className="chat-wrapper w-full">
        <div className="chat-header mb-4">
          <h2 className="font-bold text-xl">امروز می‌خواهید چه چیزی را تحلیل کنید؟</h2>
        </div>

        <div className="chat-input relative">
          <div className="absolute right-3 top-2">
            <Select value={selectedAgent} onValueChange={setSelectedAgent}>
              <SelectTrigger className="w-[120px] text-xs rounded-xl">
                <SelectValue placeholder="انتخاب ایجنت" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="agent1">ایجنت ۱</SelectItem>
                <SelectItem value="agent2">ایجنت ۲</SelectItem>
                <SelectItem value="agent3">ایجنت ۳</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="داده‌ها را متصل کنید و گفت‌وگو را شروع کنید!"
            onKeyPress={handleKeyPress}
            className="pt-18 pb-5"
          />

          <button
            type="button"
            onClick={handleSend}
            disabled={!query || isSending}
            className={`absolute inset-y-16 left-2 flex items-center justify-center w-6 h-6 rounded-full transition duration-300 ${
              !query || isSending
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:opacity-90"
            }`}
          >
            <ArrowUp size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

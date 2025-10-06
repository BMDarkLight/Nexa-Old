"use client";
import React, { useState, useEffect } from "react";
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

interface Agent {
  _id: string;
  name: string;
  description: string;
  org: string;
  model: string;
  temperature: number;
  tools: string[];
  connector_ids: string[];
  created_at: string;
  updated_at: string;
}

export default function StartChat() {
  const [query, setQuery] = useState("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [authHeader, setAuthHeader] = useState<string>("");

  const router = useRouter();

  const API_Base_Url =
    process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
  const End_point_ask = "/ask";
  const End_point_agents = "/agents";
  const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

  useEffect(() => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";
    if (!token) {
      alert("لطفاً ابتدا وارد حساب کاربری خود شوید");
      router.push("/login");
      return;
    }
    setAuthHeader(`${tokenType} ${token}`);
    console.log("[AUTH] Header set:", `${tokenType} ${token.substring(0, 10)}...`);
  }, [router]);

  useEffect(() => {
    if (!authHeader) return;
    const fetchAgents = async () => {
      const fullUrl = `${API_Base_Url}:${API_PORT}${End_point_agents}`;
      console.log("[FETCH AGENTS] URL:", fullUrl);

      try {
        const res = await fetch(fullUrl, {
          headers: {
            Authorization: authHeader,
            "Content-Type": "application/json",
          },
        });

        console.log("[FETCH AGENTS] Status:", res.status);

        if (res.status === 401) {
          console.warn("[FETCH AGENTS] 401 Unauthorized");
          alert("مدت زمان نشست شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          console.error("[FETCH AGENTS] Failed response:", await res.text());
          return;
        }

        const data: Agent[] = await res.json();
        console.log("[FETCH AGENTS] Success:", data);
        setAgents(data);
      } catch (error) {
        console.error("[FETCH AGENTS] Error:", error);
      }
    };
    fetchAgents();
  }, [authHeader, router]);

  const handleSend = async () => {
    if (!query || !authHeader) {
      alert("لطفاً یک پیام وارد کنید");
      return;
    }

    setIsSending(true);
    const fullUrl = `${API_Base_Url}:${API_PORT}${End_point_ask}`;
    const sessionId = Math.random().toString(36).substring(2, 18);
    const body: any = { query, session_id: sessionId };
    if (selectedAgent) body.agent_id = selectedAgent;

    console.log("[SEND MESSAGE] URL:", fullUrl);
    console.log("[SEND MESSAGE] Body:", body);

    try {
      const res = await fetch(fullUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authHeader,
        },
        body: JSON.stringify(body),
      });

      console.log("[SEND MESSAGE] Status:", res.status);
      console.log("[SEND MESSAGE] Headers:", Object.fromEntries(res.headers.entries()));

      if (res.status === 401) {
        console.warn("[SEND MESSAGE] 401 Unauthorized");
        alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        const errorText = await res.json();
        console.error("[SEND MESSAGE] Failed:", errorText.detail);
        alert(`خطا در ارسال پرسش: ${errorText.detail}`);
        return;
      }

      try {
        const reader = res.body?.getReader();
        if (reader) {
          const decoder = new TextDecoder();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            console.log("[STREAM CHUNK]:", chunk);
          }
        } else {
          const text = await res.json();
          console.log("[NON-STREAM RESPONSE]:", text.detail);
        }
      } catch (streamErr) {
        console.error("[STREAM ERROR]:", streamErr);
        alert("خطایی ناشناخته در خواندن پاسخ رخ داده است");
      }

      const responseSessionId = res.headers.get("X-Session-Id") || sessionId;
      console.log("[SESSION ID]:", responseSessionId);

      router.push(`/dashboard/chatbot/${responseSessionId}`);
    } catch (err) {
      console.error("[SEND MESSAGE] Network/Unhandled Error:", err);
      alert("خطا در ارسال پرسش. لطفاً دوباره تلاش کنید");
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
          <h2 className="font-bold text-xl">
            امروز می‌خواهید چه چیزی را تحلیل کنید؟
          </h2>
        </div>

        <div className="chat-input relative">
          <div className="absolute right-3 top-2">
            <Select value={selectedAgent} onValueChange={setSelectedAgent}>
              <SelectTrigger className="w-[150px] text-xs rounded-xl">
                <SelectValue placeholder="انتخاب ایجنت" />
              </SelectTrigger>
              <SelectContent>
                {agents.map((agent) => (
                  <SelectItem key={agent._id} value={agent._id}>
                    {agent.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="داده‌ها را متصل کنید و گفت‌وگو را شروع کنید!"
            onKeyPress={handleKeyPress}
            className="pt-18 pb-5 text-xs md:text-base"
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

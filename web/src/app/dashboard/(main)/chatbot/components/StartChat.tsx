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
  const router = useRouter();

  const token = Cookie.get("auth_token") ?? "";
  const tokenType = Cookie.get("token_type") ?? "Bearer";
  const authHeader = `${tokenType} ${token}`;

  const API_Base_Url =
    process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
  const End_point_ask = "/ask";
  const End_point_agents = "/agents";

  // get agents list
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch(`${API_Base_Url}${End_point_agents}`, {
          headers: {
            Authorization: authHeader,
            "Content-Type": "application/json",
          },
        });
        if (!res.ok) throw new Error("Error fetching agents");
        const data: Agent[] = await res.json();
        setAgents(data);
      } catch (err) {
        console.error("Failed to fetch agents:", err);
      }
    };
    fetchAgents();
  }, []);

  // handle sessions + session id
  const handleSend = async () => {
    if (!query) return;

    setIsSending(true);
    try {
      const sessionId = Math.random().toString(36).substring(2, 18);

      const body: any = { query, session_id: sessionId };
      if (selectedAgent) body.agent_id = selectedAgent;

      const res = await fetch(`${API_Base_Url}${End_point_ask}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authHeader,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error("Error in /ask request");

      // consume 
      try {
        const reader = res.body?.getReader();
        if (reader) {
          const decoder = new TextDecoder();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            decoder.decode(value, { stream: true }); // فقط مصرف می‌کنیم
          }
        } else {
          await res.clone().text();
        }
      } catch (err) {
        console.warn("Reading /ask response stream failed:", err);
      }

      const responseSessionId = res.headers.get("X-Session-Id") || sessionId;

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

"use client";

import React, { useState, useEffect, useRef } from "react";
import { Textarea } from "@/components/ui/textarea";
import { ArrowUp, Edit, Copy, Check, User } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import Cookie from "js-cookie";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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

interface ChatMessage {
  user: string;
  bot?: string;
  message_num?: string;
  agent_id?: string | null;
  agent_name?: string | null;
}

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point_ask = "/ask";
const End_point_agents = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

export default function Chatbot() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.session_id as string;

  const [query, setQuery] = useState<string>("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isBotTyping, setIsBotTyping] = useState<boolean>(false);
  const [username, setUsername] = useState<string>("کاربر");

  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [isEditingSending, setIsEditingSending] = useState<boolean>(false);

  const [authHeader, setAuthHeader] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // check token
  useEffect(() => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";
    if (!token) {
      alert("ابتدا وارد حساب کاربری خود شوید");
      router.push("/login");
      return;
    }
    setAuthHeader(`${tokenType} ${token}`);
  }, [router]);

  // get username
  useEffect(() => {
    if (!authHeader) return;
    const fetchUser = async () => {
      try {
        const res = await fetch(`${API_Base_Url}:${API_PORT}/users`, {
          headers: {
            Authorization: authHeader,
            "Content-Type": "application/json",
          },
        });

        if (res.status === 401) {
          alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          return;
        }

        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setUsername(data[0].username || "کاربر");
        }
      } catch {
        //
      }
    };
    fetchUser();
  }, [authHeader, router]);

  // get agents
  useEffect(() => {
    if (!authHeader) return;
    const fetchAgents = async () => {
      try {
        setIsLoading(true);
        const res = await fetch(
          `${API_Base_Url}:${API_PORT}${End_point_agents}`,
          {
            headers: {
              Authorization: authHeader,
              "Content-Type": "application/json",
            },
          }
        );

        if (res.status === 401) {
          alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          alert("خطا در دریافت لیست ایجنت‌ها");
          return;
        }

        const data: Agent[] = await res.json();
        setAgents(data);
      } catch {
        alert("خطا در دریافت لیست ایجنت‌ها");
      } finally {
        setIsLoading(false);
      }
    };
    fetchAgents();
  }, [authHeader, router]);

  // get history chat
  useEffect(() => {
    if (!authHeader || !sessionId) return;
    const fetchSessionHistory = async (retry = 3, delay = 1000) => {
      try {
        const res = await fetch(
          `${API_Base_Url}:${API_PORT}/sessions/${sessionId}`,
          {
            headers: {
              Authorization: authHeader,
              "Content-Type": "application/json",
            },
          }
        );

        if (res.status === 401) {
          alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (res.status === 404 && retry > 0) {
          setTimeout(() => fetchSessionHistory(retry - 1, delay), delay);
          return;
        }

        if (!res.ok) {
          return;
        }

        const data = await res.json();
        setChatHistory(
          data.chat_history.map((msg: any, idx: number) => ({
            user: msg.user,
            bot: msg.assistant,
            message_num: idx.toString(),
            agent_id: msg.agent_id,
            agent_name: msg.agent_name,
          }))
        );

        if (data.chat_history?.length > 0) {
          const lastAgentId =
            data.chat_history[data.chat_history.length - 1].agent_id;
          if (lastAgentId) setSelectedAgent(lastAgentId);
        }

        scrollToBottom();
      } catch {
        //
      }
    };

    fetchSessionHistory();
  }, [authHeader, sessionId, router]);

  // handle send
  const handleSend = async () => {
    if (!query || !authHeader) return;

    const userMessage = query;
    const agentName = agents.find((a) => a._id === selectedAgent)?.name || null;
    setChatHistory((prev) => [
      ...prev,
      {
        user: userMessage,
        message_num: prev.length.toString(),
        agent_id: selectedAgent,
        agent_name: agentName,
      },
    ]);

    setQuery("");
    setIsSending(true);
    setIsBotTyping(true);

    try {
      const body: any = { query: userMessage, session_id: sessionId };
      if (selectedAgent) body.agent_id = selectedAgent;

      const response = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point_ask}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: authHeader,
          },
          body: JSON.stringify(body),
        }
      );

      if (response.status === 401) {
        alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
        router.push("/login");
        return;
      }

      if (!response.ok) {
        alert("خطا در ارسال پرسش");
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let botMessage = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          botMessage += decoder.decode(value, { stream: true });
          setChatHistory((prev) => {
            const updated = [...prev];
            updated[updated.length - 1].bot = botMessage;
            return updated;
          });
          scrollToBottom();
        }
      }
    } catch {
      alert("خطا در ارسال پرسش");
    } finally {
      setIsSending(false);
      setIsBotTyping(false);
    }
  };

  // handle edit btn
const handleSaveEdit = async (index: number) => {
  if (index === null || !authHeader) return;
  const msg = chatHistory[index];
  if (!msg?.message_num) return;

  setIsEditingSending(true);

  try {
    const body = {
      query: editValue,
      session_id: sessionId,
      agent_id: selectedAgent,
    };

    const response = await fetch(
      `${API_Base_Url}:${API_PORT}/ask/edit/${msg.message_num}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authHeader,
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.log("❌ خطای ویرایش:", errorText);
      return;
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let botMessage = "";

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        botMessage += decoder.decode(value, { stream: true });

        setChatHistory((prev) => {
          const updated = [...prev];
          updated[index].user = editValue;
          updated[index].bot = botMessage;
          updated[index].agent_name =
            agents.find((a) => a._id === selectedAgent)?.name || null;
          return updated;
        });
        scrollToBottom();
      }
    }

    setEditingIndex(null);
    setEditValue("");
  } catch {
    alert("خطا در ویرایش پیام");
  } finally {
    setIsEditingSending(false);
  }
};


  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && query && !isSending) {
      e.preventDefault();
      handleSend();
    }
  };

  // handle loading for show agent messages
  const TypingIndicator = () => (
    <span className="flex items-center gap-1">
      <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-75"></span>
      <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-150"></span>
      <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-300"></span>
    </span>
  );

  // handle copy messages
  const CopyButton = ({ text }: { text: string }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
      try {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      } catch {
        alert("کپی کردن متن با خطا مواجه شد");
      }
    };
    return (
      <span onClick={handleCopy} className="cursor-pointer">
        {copied ? (
          <Check size={16} className="mt-2" />
        ) : (
          <Copy size={16} className="mt-2" />
        )}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="h-[94vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Spinner className="w-8 h-8" />
          <p className="text-gray-600">در حال بارگذاری چت...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] md:h-[100vh] flex flex-col md:w-[85%] w-[100%] mx-auto">
      <div className="flex-1 overflow-y-auto py-6 px-1 w-full">
        {chatHistory.map((chat, idx) => (
          <div key={idx} className="mb-2 flex flex-col gap-1">
            <div className="flex items-center gap-2 group">
              <div className="group w-full">
                <div className="flex gap-2 items-start">
                  <span className="inline-flex w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <User size={18} className="text-white" />
                  </span>
                  {editingIndex === idx ? (
                    <div className="flex gap-2 flex-1">
                      <Textarea
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="flex-1"
                      />
                      <button
                        onClick={() => {
                          if (editingIndex !== null)
                            handleSaveEdit(editingIndex);
                        }}
                        disabled={isEditingSending}
                        className={`px-2 text-white rounded ${
                          isEditingSending
                            ? "bg-blue-300 cursor-not-allowed"
                            : "bg-blue-500"
                        }`}
                      >
                        ذخیره
                      </button>
                      <button
                        onClick={() => setEditingIndex(null)}
                        disabled={isEditingSending}
                        className="px-2 bg-gray-400 text-white rounded"
                      >
                        لغو
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col justify-center">
                      <div className="font-bold">{username}</div>
                      <div className="mt-1">{chat.user}</div>
                    </div>
                  )}
                </div>
                {editingIndex !== idx && (
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <CopyButton text={chat.user} />
                    <Edit
                      size={16}
                      className="cursor-pointer mt-2"
                      onClick={() => {
                        setEditingIndex(idx);
                        setEditValue(chat.user);
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
            {chat.bot ? (
              <div className="mt-5 group">
                <div className="flex gap-2 items-start">
                  <div className="w-8">
                    <img src="/Squad/Login/chatbot.png" alt="bot" />
                  </div>
                  <div className="flex-1">
                    <p className="font-bold">{chat.agent_name || "نکسا"}</p>
                    <div className="mt-2 prose prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {chat.bot}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <CopyButton text={chat.bot} />
                </div>
              </div>
            ) : isBotTyping && idx === chatHistory.length - 1 ? (
              <div className="flex items-center gap-2">
                <TypingIndicator />
              </div>
            ) : null}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="sticky bottom-0 bg-background p-2 border-t md:border-t-0">
        <div className="border border-input rounded-xl bg-transparent p-2 shadow-xs w-full">
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="گفتگو کنید"
            onKeyPress={handleKeyPress}
            className="text-base border-0 shadow-none bg-transparent p-0 focus:ring-0"
          />
          
          <div className="flex items-center justify-between mt-2">
            <Select
              value={selectedAgent}
              onValueChange={(val) => setSelectedAgent(val)}
            >
              <SelectTrigger className="text-base rounded-full px-4 py-2 w-auto" size="sm">
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

            <button
              type="button"
              onClick={handleSend}
              disabled={!query || isSending}
              className={`flex items-center justify-center w-8 h-8 rounded-full transition duration-300 ${
                !query || isSending
                  ? "bg-gray-400 text-white cursor-not-allowed"
                  : "bg-blue-600 text-white hover:opacity-90"
              }`}
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

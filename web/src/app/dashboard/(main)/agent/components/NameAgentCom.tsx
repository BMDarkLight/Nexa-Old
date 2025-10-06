"use client";
import React, { useState } from "react";
import ReturnBtn from "./ReturnBtn";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAgent } from "@/app/dashboard/context/AgentsContext";
import { useRouter } from "next/navigation";
import Cookie from "js-cookie";
import { toast } from "sonner";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

export default function NameAgentCom() {
  const { agent, setField } = useAgent();
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";

    if (!token) {
      alert("ابتدا وارد حساب کاربری خود شوید");
      router.push("/login");
      return;
    }

    try {
      setSaving(true);

      const payload = {
        name: agent.name,
        description: agent.description ?? "",
        model: agent.model ?? "gpt-3.5-turbo",
        temperature: agent.temperature ?? 0.7,
        tools: agent.tools ?? [],
      };

      const res = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
        method: "POST",
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        toast.error("خطا در ایجاد ایجنت لطفا مجددا تلاش کنید.", {
          icon: null,
          style: {
            background: "#DC2626",
            color: "#fff",
          },
          duration: 2000,
        });
        return;
      }

      const newAgent = await res.json();
      const agentId = newAgent._id;

      if (agent.connector_ids && agent.connector_ids.length > 0) {
        for (const connectorId of agent.connector_ids) {
          const connectorRes = await fetch(
            `${API_Base_Url}:${API_PORT}${End_point}/${agentId}/connectors/${connectorId}`,
            {
              method: "POST",
              headers: {
                Authorization: `${tokenType} ${token}`,
                "Content-Type": "application/json",
              },
            }
          );

          if (!connectorRes.ok) {
            toast.error("ارتباط با سرور برقرار نشد.", {
              icon: null,
              style: {
                background: "#DC2626",
                color: "#fff",
              },
              duration: 2000,
            });
          }
        }
      }

      toast.success("ایجنت با موفقیت ساخته شد.", {
        icon: null,
        style: {
          background: "#2A9D90",
          color: "#fff",
        },
        duration: 2000,
      });
      router.push("/dashboard/agent");
    } catch {
      toast.error("ارتباط با سرور برقرار نشد.", {
        icon: null,
        style: {
          background: "#DC2626",
          color: "#fff",
        },
        duration: 2000,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
      <div className="flex flex-col gap-5">
        <h2 className="text-xl font-medium mt-5 md:mt-0">
          اطلاعات ایجنت را وارد کنید
        </h2>
        <div className="w-full">
          <Label htmlFor="name-agent" className="mb-3">
            نام ایجنت
          </Label>
          <Input
            id="name-agent"
            type="text"
            placeholder="نام ایجنت"
            value={agent.name}
            onChange={(e) => setField("name", e.target.value)}
          />
        </div>
      </div>

      <div className="flex justify-end items-center gap-3">
        <ReturnBtn />
        <Button
          className="cursor-pointer flex-1 md:flex-0"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "در حال ذخیره..." : "ذخیره"} <Check />
        </Button>
      </div>
    </div>
  );
}

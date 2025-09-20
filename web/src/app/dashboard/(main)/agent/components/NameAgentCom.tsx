"use client"
import React from "react";
import ReturnBtn from "./ReturnBtn";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAgent } from "@/app/dashboard/context/AgentsContext";
import { useRouter } from "next/navigation";
import Cookie from "js-cookie";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = "/agents";

export default function NameAgentCom() {
  const { agent, setField } = useAgent();
  const router = useRouter();

  const handleSave = async () => {
    try {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";

      if (!token) {
        console.error("توکن در کوکی پیدا نشد");
        return;
      }

      const payload = {
        name: agent.name,
        description: agent.description ?? "",
        model: agent.model ?? "gpt-3.5-turbo",
        temperature: agent.temperature ?? 0.7,
        tools: agent.tools ?? [],
      };

      const res = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        console.error("خطا در ایجاد ایجنت:", data.detail);
        return;
      }

      const newAgent = await res.json();
      const agentId = newAgent._id;

      if (agent.connector_ids && agent.connector_ids.length > 0) {
        for (const connectorId of agent.connector_ids) {
          try {
            const connectorRes = await fetch(
              `${API_Base_Url}${End_point}/${agentId}/connectors/${connectorId}`,
              {
                method: "POST",
                headers: {
                  Authorization: `${tokenType} ${token}`,
                  "Content-Type": "application/json",
                },
              }
            );

            if (!connectorRes.ok) {
              const errorData = await connectorRes.json();
              console.error(
                `خطا در افزودن کانکتور ${connectorId} به ایجنت:`,
                errorData.detail
              );
            }
          } catch (err) {
            console.error(
              `اشکال در افزودن کانکتور ${connectorId} به ایجنت:`,
              err
            );
          }
        }
      }

      router.push("/dashboard/agent");
    } catch (error) {
      console.error("خطا در ذخیره ایجنت:", error);
    }
  };

  return (
    <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
      <div className="flex flex-col gap-5">
        <h2 className="text-xl font-medium mt-5 md:mt-0">
          اطلاعات ایجنت را وارد کنید
        </h2>
        <div className="w-full md:w-[80%]">
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
        >
          ذخیره <Check />
        </Button>
      </div>
    </div>
  );
}

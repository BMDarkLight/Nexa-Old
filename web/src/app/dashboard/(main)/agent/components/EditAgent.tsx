"use client"
import React, { useEffect, useState } from "react";
import ReturnBtn from "./ReturnBtn";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRouter } from "next/navigation";
import Cookie from "js-cookie";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = "/agents";

interface EditAgentProps {
  agentId: string;
}

export default function EditAgent({ agentId }: EditAgentProps) {
  const [name, setName] = useState(""); 
  const router = useRouter();

  useEffect(() => {
    if (!agentId) return;

    const fetchAgent = async () => {
      try {
        const token = Cookie.get("auth_token");
        const tokenType = Cookie.get("token_type") ?? "Bearer";
        if (!token) return;

        const res = await fetch(`${API_Base_Url}${End_point}/${agentId}`, {
          headers: {
            Authorization: `${tokenType} ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (res.ok) {
          const data = await res.json();
          setName(data.name || "");
        } else {
          console.error("خطا در گرفتن اطلاعات ایجنت");
        }
      } catch (err) {
        console.error("خطا در گرفتن ایجنت:", err);
      }
    };

    fetchAgent();
  }, [agentId]);

  const handleSave = async () => {
    try {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";

      if (!token) {
        console.error("توکن در کوکی پیدا نشد");
        return;
      }

      if (!agentId) {
        console.error("agentId پیدا نشد");
        return;
      }

      if (!name || name.trim() === "") {
        alert("نام ایجنت نمی‌تواند خالی باشد.");
        return;
      }

      const payload = { name };

      const res = await fetch(`${API_Base_Url}${End_point}/${agentId}`, {
        method: "PUT",
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        console.error("خطا در بروزرسانی ایجنت:", data.detail);
        return;
      }

      router.push("/dashboard/agent");
    } catch (error) {
      console.error("خطا در ذخیره ایجنت:", error);
    }
  };

  return (
    <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
      <div className="flex flex-col gap-5">
        <h2 className="text-xl font-medium mt-5">
          تغییرات ایجنت را وارد کنید
        </h2>
        <div className="w-full">
          <Label htmlFor="name-agent" className="mb-3">
            نام ایجنت
          </Label>
          <Input
            id="name-agent"
            type="text"
            placeholder="نام ایجنت"
            value={name}
            onChange={(e) => setName(e.target.value)} // تغییر مقدار name
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

"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Check } from "lucide-react";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = "/connectors";

export default function NewConnector() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [selectedConnector, setSelectedConnector] = useState<string>("");

  const handleSubmit = async () => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";

    if (!token || !selectedConnector || !name) {
      alert("لطفا نام اتصال و یک نوع اتصال را انتخاب کنید");
      return;
    }

    try {
      const res = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `${tokenType} ${token}`,
        },
        body: JSON.stringify({
          name,
          connector_type: selectedConnector,
          settings: {},
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        console.error("خطا در ایجاد کانکتور:", errorData);

        if (
          errorData?.detail &&
          typeof errorData.detail === "string" &&
          errorData.detail.toLowerCase().includes("duplicate")
        ) {
          alert(
            "این نام برای اتصال خود قبلا استفاده شده است. لطفا نام دیگری را انتخاب کنید"
          );
        } else {
          alert("این نام برای اتصال خود قبلا استفاده شده است. لطفا نام دیگری را انتخاب کنید");
        }

        return;
      }

      router.push("/dashboard/connector");
    } catch (err) {
      console.error(err);
      alert("خطا در ایجاد اتصال");
    }
  };

  return (
    <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
      <div className="flex flex-col gap-5">
        <h2 className="text-xl font-medium mt-5 md:mt-5">
          اطلاعات اتصال خود را وارد کنید
        </h2>

        <div className="w-full">
          <Label htmlFor="name-connector" className="mb-3">
            نام اتصال
          </Label>
          <Input
            id="name-connector"
            type="text"
            placeholder="نام اتصال"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="w-full flex flex-col gap-2">
          <Label className="mb-2">نوع اتصال</Label>
          <div className="flex flex-col gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="connector_type"
                value="google_sheet"
                checked={selectedConnector === "google_sheet"}
                onChange={(e) => setSelectedConnector(e.target.value)}
              />
              <span>گوگل شیت</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="connector_type"
                value="google_drive"
                checked={selectedConnector === "google_drive"}
                onChange={(e) => setSelectedConnector(e.target.value)}
              />
              <span>گوگل درایو</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="connector_type"
                value="source_pdf"
                checked={selectedConnector === "source_pdf"}
                onChange={(e) => setSelectedConnector(e.target.value)}
              />
              <span>فایل PDF</span>
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-end items-center gap-3">
        <Button
          className="cursor-pointer flex-1 md:flex-0"
          onClick={handleSubmit}
        >
          ذخیره <Check />
        </Button>
      </div>
    </div>
  );
}

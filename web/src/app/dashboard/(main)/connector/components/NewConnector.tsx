"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Check } from "lucide-react";
import ReturnBtn from "../../agent/components/ReturnBtn";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = "/connectors";

export default function NewConnector() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [selectedConnectors, setSelectedConnectors] = useState<string[]>([]);

  const handleCheckboxChange = (value: string) => {
    if (selectedConnectors.includes(value)) {
      setSelectedConnectors(selectedConnectors.filter((v) => v !== value));
    } else {
      setSelectedConnectors([...selectedConnectors, value]);
    }
  };

  const handleSubmit = async () => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";

    if (!token || selectedConnectors.length === 0 || !name) {
      alert("لطفا نام اتصال و حداقل یک نوع اتصال را انتخاب کنید");
      return;
    }

    try {
      for (const connectorType of selectedConnectors) {
        const res = await fetch(`${API_Base_Url}${End_point}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `${tokenType} ${token}`,
          },
          body: JSON.stringify({
            name,
            connector_type: connectorType,
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
      }

      router.push("/dashboard/connector");
    } catch (err) {
      console.error(err);
      alert("خطا در ایجاد کانکتورها");
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
          <div className="flex gap-5">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedConnectors.includes("google_sheet")}
                onCheckedChange={() => handleCheckboxChange("google_sheet")}
              />
              <span>گوگل شیت</span>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedConnectors.includes("google_drive")}
                onCheckedChange={() => handleCheckboxChange("google_drive")}
              />
              <span>گوگل درایو</span>
            </div>
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

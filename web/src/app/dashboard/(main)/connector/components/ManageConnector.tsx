"use client";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Check } from "lucide-react";
import Cookie from "js-cookie";
import { useRouter, useParams } from "next/navigation";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";

export default function ManageConnector() {
  const router = useRouter();
  const params = useParams();
  const connectorId = params.connectorId;

  const [name, setName] = useState("");
  const [selectedConnectors, setSelectedConnectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConnector = async () => {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";

      if (!token) {
        alert("توکن پیدا نشد.");
        return;
      }

      try {
        const res = await fetch(`${API_Base_Url}/connectors/${connectorId}`, {
          method: "GET",
          headers: {
            Authorization: `${tokenType} ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (!res.ok) {
          console.error("Failed to fetch connector");
          return;
        }

        const data = await res.json();
        setName(data.name || "");

        const types: string[] = [];
        if (data.connector_type === "google_sheet") types.push("google_sheet");
        if (data.connector_type === "google_drive") types.push("google_drive");

        if (Array.isArray(data.connector_type)) {
          data.connector_type.forEach((type: string) => types.push(type));
        }

        setSelectedConnectors(types);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching connector:", err);
      }
    };

    fetchConnector();
  }, [connectorId]);

  const handleCheckboxChange = (value: string) => {
    if (selectedConnectors.includes(value)) {
      setSelectedConnectors(selectedConnectors.filter((v) => v !== value));
    } else {
      setSelectedConnectors([...selectedConnectors, value]);
    }
  };

  const handleSave = async () => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";

    if (!token || !name || selectedConnectors.length === 0) {
      alert("لطفا نام اتصال و حداقل یک نوع اتصال را انتخاب کنید");
      return;
    }

    try {
      const res = await fetch(`${API_Base_Url}/connectors/${connectorId}`, {
        method: "PUT",
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          connector_type: selectedConnectors.length === 1 ? selectedConnectors[0] : selectedConnectors,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        console.error("خطا در آپدیت کانکتور:", errorData);
        alert("خطا در ذخیره تغییرات");
        return;
      }

      alert("تغییرات با موفقیت ذخیره شد");
      router.push("/dashboard/connector");
    } catch (err) {
      console.error(err);
      alert("خطا در ذخیره تغییرات");
    }
  };

  if (loading) {
    return <p>در حال بارگذاری اطلاعات کانکتور...</p>;
  }

  return (
    <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
      <div className="flex flex-col gap-5">
        <h2 className="text-xl font-medium mt-5 md:mt-5">
          تغییرات اتصال خود را وارد کنید
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
          onClick={handleSave}
        >
          ذخیره <Check />
        </Button>
      </div>
    </div>
  );
}

"use client";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import Cookie from "js-cookie";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.65";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

export default function EditAgent() {
  const { agentId } = useParams();
  const router = useRouter();

  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchAgent = async () => {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";

      if (!token) {
        alert("ابتدا وارد حساب کاربری خود شوید");
        router.push("/login");
        return;
      }

      try {
        const res = await fetch(`${API_Base_Url}:${API_PORT}/agents/${agentId}`, {
          method: "GET",
          headers: {
            Authorization: `${tokenType} ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (res.status === 401) {
          alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          alert("ایجنت مورد نیاز یافت نشد");
          return;
        }

        const data = await res.json();
        setName(data.name || "");
      } catch {
        alert("ایجنت مورد نیاز یافت نشد");
      } finally {
        setLoading(false);
      }
    };

    fetchAgent();
  }, [agentId]);

  const handleSave = async () => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";

    if (!token || !name) {
      alert("لطفا نام ایجنت را وارد کنید");
      return;
    }

    try {
      setSaving(true);

      const res = await fetch(`${API_Base_Url}:${API_PORT}/agents/${agentId}`, {
        method: "PUT",
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      });

      if (res.status === 401) {
        alert("مدت زمان موندن شما منقضی شده است. لطفاً دوباره وارد شوید");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        alert("خطا در ذخیره تغییرات");
        return;
      }

      router.push(`/dashboard/agent/new-agent/uploadFile-agent/${agentId}`);
    } catch {
      alert("ثبت تغییرات با مشکل روبرو شد");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <Spinner className="w-8 h-8" />
          <p className="text-gray-600">در حال بارگذاری اطلاعات ایجنت...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 lg:px-5 h-[100vh] md:h-auto">
      <h2 className="text-xl font-medium mt-5 md:mt-5">مدیریت ایجنت</h2>

      <div className="w-full">
        <Label htmlFor="name-agent" className="mb-3">
          نام ایجنت
        </Label>
        <Input
          id="name-agent"
          type="text"
          placeholder="نام ایجنت"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      <div className="flex justify-end items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <>
              <Spinner className="w-4 h-4 mr-2" />
              در حال ذخیره...
            </>
          ) : (
            "مرحله بعد"
          )}
        </Button>
      </div>
    </div>
  );
}

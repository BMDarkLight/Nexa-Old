"use client";
import React, { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Check, Trash2 } from "lucide-react";
import Cookie from "js-cookie";
import { useRouter, useParams, useSearchParams } from "next/navigation";

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

export default function ManageConnector() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const connectorId = params.connectorId as string;
  const connectorTypeFromUrl = searchParams.get("type");

  const [name, setName] = useState("");
  const [selectedConnectors, setSelectedConnectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [uri, setUri] = useState(""); // برای نگهداری URL
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const fetchConnector = async () => {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type") ?? "Bearer";

      if (!token) {
        alert("ابتدا وارد حساب کاربری خود شوید");
        router.push("/login");
        return;
      }

      try {
        const res = await fetch(
          `${API_Base_Url}:${API_PORT}/connectors/${connectorId}`,
          {
            method: "GET",
            headers: {
              Authorization: `${tokenType} ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (res.status === 401) {
          alert("مدت زمان نشست شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          alert("خطا در بارگذاری اطلاعات کانکتور");
          return;
        }

        const data = await res.json();
        setName(data.name || "");

        const types: string[] = [];
        if (data.connector_type === "google_sheet") types.push("google_sheet");
        if (data.connector_type === "google_drive") types.push("google_drive");
        if (data.connector_type === "source_pdf") types.push("source_pdf");
        if (data.connector_type === "source_uri") types.push("source_uri");

        if (Array.isArray(data.connector_type)) {
          data.connector_type.forEach((type: string) => types.push(type));
        }

        setSelectedConnectors(types);

        // اگر قبلاً setting داشته باشه مقدار uri رو بیاریم
        if (data.settings && data.settings.uri) {
          setUri(data.settings.uri);
        }
      } catch {
        alert("خطا در بارگذاری اطلاعات کانکتور");
      } finally {
        setLoading(false);
      }
    };

    fetchConnector();
  }, [connectorId, router]);

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

    if (!token) {
      alert("ابتدا وارد حساب کاربری خود شوید");
      router.push("/login");
      return;
    }

    if (!name || selectedConnectors.length === 0) {
      alert("لطفا نام اتصال و حداقل یک نوع اتصال را انتخاب کنید");
      return;
    }

    try {
      setSaving(true);

      const res = await fetch(
        `${API_Base_Url}:${API_PORT}/connectors/${connectorId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `${tokenType} ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name,
            connector_type:
              selectedConnectors.length === 1
                ? selectedConnectors[0]
                : selectedConnectors,
          }),
        }
      );

      if (res.status === 401) {
        alert("مدت زمان نشست شما منقضی شده است. لطفاً دوباره وارد شوید");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        alert("خطا در ذخیره تغییرات");
        return;
      }

      // هندل آپلود برای PDF و Excel
      if (
        (connectorTypeFromUrl === "source_pdf" ||
          connectorTypeFromUrl === "google_sheet") &&
        fileInputRef.current?.files?.length
      ) {
        const file = fileInputRef.current.files[0];
        const formData = new FormData();
        formData.append("file", file);

        const uploadRes = await fetch(
          `${API_Base_Url}:${API_PORT}/connectors/${connectorId}/upload`,
          {
            method: "POST",
            headers: {
              Authorization: `${tokenType} ${token}`,
            },
            body: formData,
          }
        );

        if (uploadRes.status === 401) {
          alert("مدت زمان نشست شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!uploadRes.ok) {
          alert(
            connectorTypeFromUrl === "source_pdf"
              ? "خطا در آپلود فایل PDF"
              : "خطا در آپلود فایل اکسل"
          );
          return;
        }
      }

      // هندل برای source_uri (ذخیره url داخل settings)
      if (connectorTypeFromUrl === "source_uri") {
        if (!uri) {
          alert("لطفاً یک آدرس URL معتبر وارد کنید");
          return;
        }

        const uriRes = await fetch(
          `${API_Base_Url}:${API_PORT}/connectors/${connectorId}/settings`,
          {
            method: "PUT",
            headers: {
              Authorization: `${tokenType} ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              settings: { uri },
            }),
          }
        );

        if (uriRes.status === 401) {
          alert("مدت زمان نشست شما منقضی شده است. لطفاً دوباره وارد شوید");
          router.push("/login");
          return;
        }

        if (!uriRes.ok) {
          alert("خطا در ذخیره URL اتصال");
          return;
        }
      }

      alert("تغییرات با موفقیت ذخیره شد");
      router.push("/dashboard/connector");
    } catch {
      alert("خطا در ذخیره تغییرات");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";

    if (!token) {
      alert("ابتدا وارد حساب کاربری خود شوید");
      router.push("/login");
      return;
    }

    try {
      setDeleting(true);

      const res = await fetch(
        `${API_Base_Url}:${API_PORT}/connectors/${connectorId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `${tokenType} ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (res.status === 401) {
        alert("مدت زمان نشست شما منقضی شده است. لطفاً دوباره وارد شوید");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        alert("خطا در حذف اتصال داده");
        return;
      }

      alert("اتصال با موفقیت حذف شد");
      router.push("/dashboard/connector");
    } catch {
      alert("خطا در حذف اتصال داده");
    } finally {
      setDeleting(false);
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

        {connectorTypeFromUrl === "google_sheet" && (
          <div className="w-full flex flex-col gap-2">
            <Label className="mb-2">آپلود فایل اکسل</Label>
            <Input
              ref={fileInputRef}
              id="excel-upload"
              type="file"
              accept=".xlsx, .xls"
            />
          </div>
        )}

        {connectorTypeFromUrl === "google_drive" && (
          <div className="w-full flex flex-col gap-2">
            <Label className="mb-2">نوع اتصال (گوگل درایو)</Label>
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedConnectors.includes("google_drive")}
                onCheckedChange={() => handleCheckboxChange("google_drive")}
              />
              <span>گوگل درایو</span>
            </div>
          </div>
        )}

        {connectorTypeFromUrl === "source_pdf" && (
          <div className="w-full flex flex-col gap-2">
            <Label className="mb-2">آپلود فایل PDF</Label>
            <Input
              ref={fileInputRef}
              id="pdf-upload"
              type="file"
              accept="application/pdf"
            />
          </div>
        )}

        {connectorTypeFromUrl === "source_uri" && (
          <div className="w-full flex flex-col gap-2">
            <Label htmlFor="uri-input" className="mb-2">
              آدرس URL
            </Label>
            <Input
              id="uri-input"
              type="url"
              placeholder="https://example.com"
              value={uri}
              onChange={(e) => setUri(e.target.value)}
              required
            />
          </div>
        )}
      </div>

      <div className="flex justify-end items-center gap-3">
        <Button
          className="cursor-pointer flex-1 md:flex-0"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "در حال اتصال..." : "وصل"} <Check />
        </Button>

        <Button
          variant="destructive"
          className="cursor-pointer flex-1 md:flex-0"
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleting ? "در حال حذف..." : "حذف اتصال داده"} <Trash2 />
        </Button>
      </div>
    </div>
  );
}

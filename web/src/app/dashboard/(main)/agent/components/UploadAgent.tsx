"use client";

import Link from "next/link";
import Cookie from "js-cookie";
import { toast } from "sonner";
import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table";
import DeleteFile from "./DeleteFile";
import ReturnBtn from "./ReturnBtn";
import { useParams } from "next/navigation";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

interface ContextEntry {
  id: string;
  filename: string;
  size?: number;
}

export default function UploadAgent() {
  const [files, setFiles] = useState<File[]>([]);
  const [contextEntries, setContextEntries] = useState<ContextEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const { agent_id } = useParams();

  const token = Cookie.get("auth_token");
  const tokenType = Cookie.get("token_type") ?? "Bearer";

  const fetchContext = async () => {
    if (!agent_id || !token) return;

    try {
      const res = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point}/${agent_id}/context`,
        {
          method: "GET",
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
        }
      );

      if (!res.ok) throw new Error("خطا در دریافت فایل‌ها");

      const data = await res.json();
      setContextEntries(data.context_entries || []);
    } catch (err) {
      console.error(err);
      toast.error("خطا در دریافت لیست فایل‌ها", {
        style: { background: "#DC2626", color: "#fff" },
      });
    }
  };

  useEffect(() => {
    fetchContext();
  }, [agent_id]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !agent_id) return;

    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append("file", file);
    });

    try {
      setLoading(true);
      const res = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point}/${agent_id}/context`,
        {
          method: "POST",
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
          body: formData,
        }
      );

      if (!res.ok) throw new Error("خطا در آپلود فایل");

      toast.success("فایل با موفقیت آپلود شد", {
        style: { background: "#059669", color: "#fff" },
      });

      fetchContext();
    } catch (err) {
      toast.error("آپلود فایل با خطا مواجه شد", {
        style: { background: "#DC2626", color: "#fff" },
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex lg:px-10 md:items-center md:justify-center mx-auto">
        <div className="w-full flex flex-col gap-4">
          <div className="flex flex-col mt-4 md:mt-0 gap-3">
            <h2 className="text-xl font-bold">
              فایل های دانش ایجنت را آپلود کنید.
            </h2>
            <p className="text-sm text-muted-foreground md:w-[80%]">
              محتوای این فایل‌ها در حافظه ایجنت قرار می‌گیرد و هنگام پاسخ‌گویی،
              برای ارائه اطلاعات دقیق‌تر و متناسب با نیاز شما مورد استفاده قرار
              می‌گیرد.
            </p>
          </div>

          <div className="mt-6">
            <label htmlFor="fileUpload" className="cursor-pointer">
              <Button
                variant="outline"
                className="flex flex-col items-center gap-2 rounded-md cursor-pointer py-12 px-6"
                asChild
              >
                <span>
                  <Upload size={18} />
                  {loading ? "در حال آپلود..." : "برای انتخاب فایل کلیک کنید"}
                </span>
              </Button>
            </label>
            <input
              id="fileUpload"
              type="file"
              multiple
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          <div className="mt-6 border rounded-md overflow-hidden">
            {contextEntries.length > 0 ? (
              <Table>
                <TableBody>
                  {contextEntries.map((file, index) => (
                    <TableRow key={index} className="relative">
                      <TableCell className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <img
                            src="/Squad/image/mc-file-pdf.png"
                            alt=""
                            className="w-6 h-6"
                          />
                          {file.filename || "بدون نام"}
                        </div>
                        <DeleteFile />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-6 text-sm text-muted-foreground">
                هنوز فایلی آپلود نشده است.
              </div>
            )}
          </div>

          <div className="flex justify-end items-center gap-3 mt-5">
            <ReturnBtn />
            <Button className="cursor-pointer flex-1 md:flex-0">
              مرحله بعد
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

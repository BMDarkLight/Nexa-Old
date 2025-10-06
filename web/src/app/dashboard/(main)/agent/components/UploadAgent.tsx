"use client";

import Link from "next/link";
import Cookie from "js-cookie";
import { toast } from "sonner";
import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import DeleteFile from "./DeleteFile";
import ReturnBtn from "./ReturnBtn";
import { useParams, useRouter } from "next/navigation";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
const End_point = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

interface ContextEntry {
  id: string;
  filename?: string;
  size?: number;
  type?: string;
}

export default function UploadAgent() {
  const [files, setFiles] = useState<File[]>([]);
  const [contextEntries, setContextEntries] = useState<ContextEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [nextLoading, setNextLoading] = useState(false);

  const { agent_id } = useParams();
  const router = useRouter();

  const token = Cookie.get("auth_token");
  const tokenType = Cookie.get("token_type") ?? "Bearer";

  const fetchContext = async () => {
    if (!agent_id || !token) return;

    try {
      const res = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point}/${agent_id}`,
        {
          method: "GET",
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
        }
      );

      if (!res.ok) throw new Error("خطا در دریافت اطلاعات ایجنت");

      const data = await res.json();
      const contextData: ContextEntry[] =
        data.context?.map((id: string) => ({
          id,
          filename: id,
          type: "pdf",
        })) || [];
      setContextEntries(contextData);
    } catch (err) {
      console.error(err);
      toast.error("خطا در دریافت لیست فایل‌ها", {
        icon: null,
        style: { background: "#DC2626", color: "#fff" },
      });
    }
  };

  useEffect(() => {
    fetchContext();
  }, [agent_id]);

  const getFileType = (file: File): string => {
    const type = file.type;
    const name = file.name.toLowerCase();

    if (type.includes("word") || name.endsWith(".doc") || name.endsWith(".docx"))
      return "word";
    if (type.includes("sheet") || name.endsWith(".xls") || name.endsWith(".xlsx"))
      return "excel";
    if (type.includes("pdf") || name.endsWith(".pdf")) return "pdf";
    return "unknown";
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !agent_id) return;

    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);

    setLoading(true);
    try {
      for (const file of selectedFiles) {
        const fileType = getFileType(file);

        // ✅ toast بر اساس نوع فایل
        const toastMsg =
          fileType === "word"
            ? "فایل Word در حال آپلود شدن است"
            : fileType === "excel"
            ? "فایل Exel در حال آپلود شدن است"
            : fileType === "pdf"
            ? "فایل PDF در حال آپلود شدن است"
            : "📁 فایل با نوع ناشناخته در حال آپلود است...";

        toast.info(toastMsg, {
          icon: null,
          style: { background: "#2563EB", color: "#fff" },
        });

        const formData = new FormData();
        formData.append("file", file);

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

        if (!res.ok) {
          toast.error("لطفا فایل خالی نفرستید.", {
            icon: null,
            style: { background: "#DC2626", color: "#fff" },
          });
          return;
        }
      }

      toast.success("فایل‌ها با موفقیت آپلود شدند", {
        icon: null,
        style: { background: "#059669", color: "#fff" },
      });

      fetchContext();
    } catch (err) {
      toast.error("آپلود فایل با خطا مواجه شد", {
        icon: null,
        style: { background: "#DC2626", color: "#fff" },
      });
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  const getFileIcon = (filename?: string): string => {
    if (!filename) return "/Squad/image/mc-file-pdf.png";

    const lower = filename.toLowerCase();
    if (lower.endsWith(".doc") || lower.endsWith(".docx"))
      return "/Squad/image/mc-file-word.png";
    if (lower.endsWith(".xls") || lower.endsWith(".xlsx"))
      return "/Squad/image/mc-file-excel.png";
    if (lower.endsWith(".pdf")) return "/Squad/image/mc-file-pdf.png";
    return "/Squad/image/mc-file-pdf.png";
  };

  const handleNext = () => {
    setNextLoading(true);
    setTimeout(() => {
      router.push("/dashboard/agent/new-agent/name-agent");
    }, 1000);
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
                            src={getFileIcon(file.filename)}
                            alt=""
                            className="w-6 h-6"
                          />
                          فایل {index + 1}
                        </div>
                        <DeleteFile
                          agent_id={agent_id as string}
                          context_id={file.filename}
                        />
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
            <Button
              className="cursor-pointer flex-1 md:flex-0"
              onClick={handleNext}
              disabled={nextLoading}
            >
              {nextLoading ? "مرحله بعد..." : "مرحله بعد"}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

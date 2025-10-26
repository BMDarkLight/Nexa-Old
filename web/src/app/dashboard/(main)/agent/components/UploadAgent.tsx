"use client";

import Link from "next/link";
import Cookie from "js-cookie";
import { toast } from "sonner";
import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { Spinner } from "@/components/ui/spinner";
import DeleteFile from "./DeleteFile";
import ReturnBtn from "./ReturnBtn";
import { useParams, useRouter } from "next/navigation";
import Swal from "sweetalert2";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.65";
const End_point = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

interface ContextEntry {
  context_id: string;
  filename: string;
  file_key: string;
  is_tabular: boolean;
  created_at: string;
}

interface UploadingFile {
  name: string;
  isUploading: boolean;
}

export default function UploadAgent() {
  const [files, setFiles] = useState<File[]>([]);
  const [contextEntries, setContextEntries] = useState<ContextEntry[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [nextLoading, setNextLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const { agent_id } = useParams();
  const router = useRouter();

  const token = Cookie.get("auth_token");
  const tokenType = Cookie.get("token_type") ?? "Bearer";

  const fetchContext = useCallback(async (): Promise<ContextEntry[] | null> => {
    if (!agent_id || !token) return null;
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

      if (!res.ok) throw new Error("خطا در دریافت لیست فایل‌ها");

      const data: ContextEntry[] = await res.json();
      setContextEntries(data);
      return data;
    } catch (err) {
      console.error(err);
      toast.error("خطا در دریافت لیست فایل‌ها", {
        icon: null,
        style: { background: "#DC2626", color: "#fff" },
      });
      return null;
    }
  }, [agent_id, token, tokenType]);

  useEffect(() => {
    const fetchData = async () => {
      setInitialLoading(true);
      await fetchContext();
      setInitialLoading(false);
    };
    
    fetchData();
    const handleRefresh = () => fetchContext();
    window.addEventListener("refreshFiles", handleRefresh);
    return () => window.removeEventListener("refreshFiles", handleRefresh);
  }, [fetchContext]);

  // ✅ فقط csv مجاز است
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !agent_id) return;
    const selectedFiles = Array.from(e.target.files);

    // بررسی نوع فایل
    const invalidFiles = selectedFiles.filter(
      (file) => !file.name.toLowerCase().endsWith(".csv")
    );

    if (invalidFiles.length > 0) {
      toast.error("فقط فایل‌های با فرمت CSV مجاز به آپلود هستند.", {
        icon: null,
        style: { background: "#DC2626", color: "#fff" },
      });
      e.target.value = "";
      return;
    }

    setFiles(selectedFiles);
    setLoading(true);

    // فوراً فایل‌های در حال آپلود را به جدول اضافه می‌کنیم
    const newUploadingFiles: UploadingFile[] = selectedFiles.map(file => ({
      name: file.name,
      isUploading: true
    }));
    setUploadingFiles(prev => [...prev, ...newUploadingFiles]);

    let uploadToastId: string | number | undefined;
    
    try {
      for (const file of selectedFiles) {
        uploadToastId = toast.info("در حال آپلود فایل CSV ...", {
          icon: null,
          style: { background: "#2563EB", color: "#fff" },
        });

        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(
          `${API_Base_Url}:${API_PORT}${End_point}/${agent_id}/context`,
          {
            method: "POST",
            headers: { Authorization: `${tokenType} ${token}` },
            body: formData,
          }
        );

        if (!res.ok) {
          // حذف toast در حال آپلود در صورت خطا
          if (uploadToastId) {
            toast.dismiss(uploadToastId);
          }
          toast.error("خطا در آپلود فایل CSV", {
            icon: null,
            style: { background: "#DC2626", color: "#fff" },
          });
          // حذف فایل ناموفق از لیست آپلود
          setUploadingFiles(prev => prev.filter(f => f.name !== file.name));
          return;
        }

        // حذف فایل موفق از لیست آپلود
        setUploadingFiles(prev => prev.filter(f => f.name !== file.name));
      }

      // حذف toast در حال آپلود قبل از نمایش toast موفقیت
      if (uploadToastId) {
        toast.dismiss(uploadToastId);
      }
      
      toast.success("فایل با موفقیت آپلود شد و درحال پردازش است. لطفا مرحله بعد بروید.", {
        icon: null,
        style: { background: "#059669", color: "#fff" },
        duration: 6000,
      });

      await fetchContext();
    } catch (err) {
      // حذف toast در حال آپلود در صورت خطای عمومی
      if (uploadToastId) {
        toast.dismiss(uploadToastId);
      }
      toast.error("آپلود فایل با خطا مواجه شد", {
        icon: null,
        style: { background: "#DC2626", color: "#fff" },
      });
      // پاک کردن تمام فایل‌های در حال آپلود در صورت خطا
      setUploadingFiles([]);
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  const cleanFileName = (filename: string): string => {
    const parts = filename.split("_");
    if (parts.length > 1) return parts.slice(1).join("_");
    return filename.replace(/^files\//, "");
  };

  const handleNext = () => {
    setNextLoading(true);
    setTimeout(() => {
      router.push("/dashboard/agent/new-agent/name-agent");
    }, 1000);
  };

  if (initialLoading) {
    return (
      <div className="flex lg:px-10 md:items-center md:justify-center mx-auto">
        <div className="w-full flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-4">
            <Spinner className="w-8 h-8" />
            <p className="text-gray-600">در حال بارگذاری فایل‌ها...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex lg:px-10 md:items-center md:justify-center mx-auto">
      <div className="w-full flex flex-col gap-4">
        <div className="flex flex-col mt-4 md:mt-0 gap-3">
          <h2 className="text-xl font-bold">فایل های دانش ایجنت را آپلود کنید.</h2>
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
                {loading ? <Spinner className="w-4 h-4" /> : <Upload size={18} />}
                {loading ? "در حال آپلود..." : "برای انتخاب فایل CSV کلیک کنید"}
              </span>
            </Button>
          </label>
          <input
            id="fileUpload"
            type="file"
            multiple
            onChange={handleFileChange}
            className="hidden"
            accept=".csv"
          />
        </div>

        <div className="mt-6 border rounded-md overflow-hidden">
          {(contextEntries.length > 0 || uploadingFiles.length > 0) ? (
            <Table>
              <TableBody>
                {/* فایل‌های آپلود شده */}
                {contextEntries.map((file, index) => (
                  <TableRow key={`uploaded-${index}`} className="relative">
                    <TableCell className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <img
                          src="/Squad/image/mc-file-spreadsheet.png"
                          alt=""
                          className="w-6 h-6"
                        />
                        {cleanFileName(file.filename)}
                      </div>
                      <DeleteFile
                        agent_id={agent_id as string}
                        context_id={file.context_id}
                      />
                    </TableCell>
                  </TableRow>
                ))}
                
                {/* فایل‌های در حال آپلود */}
                {uploadingFiles.map((file, index) => (
                  <TableRow key={`uploading-${index}`} className="relative">
                    <TableCell className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <img
                          src="/Squad/image/mc-file-spreadsheet.png"
                          alt=""
                          className="w-6 h-6 opacity-50"
                        />
                        <span className="text-muted-foreground">{file.name}</span>
                      </div>
                      <div className="flex items-center">
                        <Spinner className="w-4 h-4" />
                      </div>
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
            {nextLoading ? (
              <>
                <Spinner className="w-4 h-4 mr-2" />
                مرحله بعد...
              </>
            ) : (
              "مرحله بعد"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

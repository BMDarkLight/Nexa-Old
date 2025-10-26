"use client";

import React, { useState } from "react";
import { Download, EllipsisVertical, Trash2 } from "lucide-react";
import Swal from "sweetalert2";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.65";
const End_point = "/agents";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";

interface DeleteFileProps {
  agent_id: string;
  context_id?: string;
}

export default function DeleteFile({ agent_id, context_id }: DeleteFileProps) {
  const router = useRouter();
  const [show, setShow] = useState(false);

  const token = Cookie.get("auth_token");
  const tokenType = Cookie.get("token_type") ?? "Bearer";

  const handleDownload = async () => {
    if (!agent_id || !context_id) return;
    setShow(false);

    try {
      const res = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point}/${agent_id}/context/${context_id}/download`,
        {
          method: "GET",
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
        }
      );

      if (!res.ok) throw new Error("دریافت لینک دانلود با خطا مواجه شد");

      const data = await res.json();

      if (data.download_url) {
        const downloadUrl = data.download_url;

        const a = document.createElement("a");
        a.href = downloadUrl;
        a.target = "_blank";
        a.download = "";
        document.body.appendChild(a);
        a.click();
        a.remove();

        toast.success("دانلود فایل آغاز شد", {
          icon: null,
          style: { background: "#059669", color: "#fff" },
        });
      } else {
        throw new Error("لینک دانلود موجود نیست");
      }
    } catch (error) {
      console.error(error);
      toast.error("دانلود فایل انجام نشد.", {
        icon: null,
        style: { background: "#DC2626", color: "#fff" },
      });
    }
  };

  const handleDelete = async () => {
    if (!agent_id || !context_id) return;

    setShow(false);
    const result = await Swal.fire({
      title: "حذف فایل",
      text: "آیا مطمئن هستید که می‌خواهید این فایل را حذف کنید؟",
      showCancelButton: true,
      cancelButtonText: "انصراف",
      confirmButtonText: "حذف",
      reverseButtons: true,
      customClass: {
        popup: "swal-rtl",
        title: "swal-title",
        confirmButton: "swal-confirm-btn swal-half-btn",
        cancelButton: "swal-cancel-btn swal-half-btn",
        htmlContainer: "swal-text",
        actions: "swal-container",
      },
    });

    if (result.isConfirmed) {
      try {
        const res = await fetch(
          `${API_Base_Url}:${API_PORT}${End_point}/${agent_id}/context/${context_id}`,
          {
            method: "DELETE",
            headers: {
              Authorization: `${tokenType} ${token}`,
            },
          }
        );

        if (!res.ok) throw new Error("خطا در حذف فایل");

        toast.success("فایل با موفقیت حذف شد", {
          icon: null,
          style: { background: "#059669", color: "#fff" },
        });

        window.dispatchEvent(new Event("refreshFiles"));
      } catch (error) {
        console.error(error);
        toast.error("حذف فایل با مشکل مواجه شد.", {
          icon: null,
          style: { background: "#DC2626", color: "#fff" },
        });
      }
    }
  };

  return (
    <>
      <div className="relative">
        <EllipsisVertical
          size={20}
          onClick={() => setShow(!show)}
          className="cursor-pointer"
        />
        {show && (
          <div
            className={`fixed z-[9999] w-26 left-5 md:w-40 bg-white dark:bg-neutral-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-md animate-in fade-in flex flex-col gap-4 p-2`}
          >
            <div
              className="flex justify-between hover:text-[#2A9D90] transition duration-400 cursor-pointer"
              onClick={handleDownload}
            >
              <p className="text-sm">دانلود</p>
              <Download size={16} />
            </div>
            <div
              className="flex justify-between hover:text-[#DC2626] transition duration-400 cursor-pointer"
              onClick={handleDelete}
            >
              <p className="text-sm">حذف</p>
              <Trash2 size={16} />
            </div>
          </div>
        )}
      </div>
    </>
  );
}

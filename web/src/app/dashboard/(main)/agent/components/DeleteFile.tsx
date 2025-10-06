"use client";

import React, { useState } from "react";
import { Download, EllipsisVertical, Trash2 } from "lucide-react";
import Swal from "sweetalert2";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4";
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

      if (!res.ok) throw new Error("دانلود فایل با خطا مواجه شد");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = context_id;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      toast.error("فایل دانلود نشد.", {
        icon:null ,
        style: { background: "#DC2626", color: "#fff" },
      });
    }
  };

  const handleDelete = async () => {
    if (!agent_id || !context_id) return;

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

        Swal.fire({
          title: "موفق!",
          text: "فایل با موفقیت حذف شد.",
          icon: "success",
          confirmButtonText: "باشه",
        }).then(() => {
          router.refresh();
        });
      } catch (error) {
        console.error(error);
        Swal.fire({
          title: "خطا!",
          text: "حذف فایل با مشکل مواجه شد.",
          icon: "error",
          confirmButtonText: "باشه",
        });
      }
    }
  };

  return (
    <>
      <div>
        <EllipsisVertical size={20} onClick={() => setShow(!show)} />
        <div
          className={`fixed z-[9999] w-26 left-5 md:w-40 bg-white dark:bg-neutral-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-md animate-in fade-in flex flex-col gap-4 p-2 ${
            show ? `block` : `hidden`
          }`}
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
      </div>
    </>
  );
}

"use client";
import React, { useState } from "react";
import { Bot, Download, EllipsisVertical, Plus, Trash2 } from "lucide-react";
import Swal from "sweetalert2";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";
const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = (process.env.NEXT_PUBLICK_ENDPOINT = "/agents");
export default function DeleteFile() {
  const router = useRouter();
  const [show, setShow] = useState(false);
  const handleDeleteAgent = async () => {
    const result = await Swal.fire({
      title: "حذف ایجنت",
      text: "آیا مطمئن هستید که می‌خواهید ایجنت فلان را حذف کنید؟",
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
          <div className="flex justify-between hover:text-[#2A9D90] transition duration-400 cursor-pointer">
            <p className="text-sm">دانلود</p>
            <Download size={16} />
          </div>
          <div className="flex justify-between hover:text-[#DC2626] transition duration-400 cursor-pointer">
            <p className="text-sm">حذف</p>
            <Trash2 size={16} />
          </div>
        </div>
      </div>
    </>
  );
}

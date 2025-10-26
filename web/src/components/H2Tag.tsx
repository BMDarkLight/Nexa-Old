"use client"
import { usePathname } from "next/navigation";
import React from "react";

export default function H2Tag(){
      const pathname = usePathname();
      if(pathname.startsWith("/dashboard/connector")) return <h2 className="font-bold text-xl">اتصال داده ها</h2>
      if(pathname.startsWith("/dashboard/agent")) return <h2 className="font-bold text-xl">ایجنت ها</h2>
      return null; 
}

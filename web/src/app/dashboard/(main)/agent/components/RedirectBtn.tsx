"use client"
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { useRouter } from "next/navigation";
import React from "react";
export default function RedirectBtn(){
      const router = useRouter()

      return(
            <>
            <Button className="cursor-pointer flex-1 md:flex-0" onClick={()=>router.push("/agent")}>ذخیره<Check/></Button>
            
            
            </>
      )
}
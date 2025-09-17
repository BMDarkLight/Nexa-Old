"use client"
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import React from "react";
export default function ReturnBtn(){
      const router = useRouter()
      return(
            <>
               <Button className="bg-secondary text-primary hover:bg-secondary/80 cursor-pointer" onClick={()=>router.back()}>بازگشت</Button>
            </>
      )
}
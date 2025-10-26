"use client"
import React from "react"
import { Button } from "./ui/button"
import { ArrowUpRight } from "lucide-react"
import { useRouter } from "next/navigation"
export default function HeroSignBtn(){
      const router = useRouter();
      return(
            <>

            <Button
              size="lg"
              className="w-full sm:w-auto rounded-full text-base cursor-pointer"
              onClick={()=>router.push("/signup")}
            >
              ثبت نام در لیست انتظار <ArrowUpRight className="!h-5 !w-5" />
            </Button>
            
            
            </>
      )
}

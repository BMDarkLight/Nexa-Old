"use client"
import React from "react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button";
import { ArrowBigLeft, ArrowLeft } from "lucide-react";
import ReturnBtn from "./ReturnBtn";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAgent } from "@/app/dashboard/context/AgentsContext";
const availableTools = ["سرچ", "ماشین حساب", "حافظه", "مرورگر"];
export default function NewAgentCom(){
      // const {agent} = useAgent()
      // console.log(agent.tools);
      
      return(
            <>
               <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
                 <div className="flex flex-col gap-5">
                   <h2 className="text-xl font-medium mt-5 md:mt-0">اتصالات ایجنت خود را انتخاب کنید</h2>
                  <div className="flex justify-between flex-wrap gap-5 lg:grid lg:grid-cols-3 lg:gap-2">
                       {availableTools.map((tool)=>(
                         <Card className="w-full" key={tool}>
                 <div className="flex ">
                  <div>
                        <picture>
                              <img src="/Squad/image/card-img.png" className="w-10" alt="" />
                        </picture>
                  </div>
                 <div className="mr-3 w-full flex justify-between items-center md:block">
                   <CardHeader className="flex-1 ">
                     <CardTitle className="text-sm font-semibold">{tool}</CardTitle>
                </CardHeader>
            <CardContent className="text-xs hidden md:block">
                 <p>جدول‌های گوگل شیت خود را تحلیل کنید.</p>
           </CardContent>
           <div className="flex justify-end md:mt-3">
            <CardFooter>
             <Switch className="flex flex-row-reverse items-center" />
       </CardFooter>
           </div>
                 </div>
                 </div>
       

            </Card>
                       ))}
                  </div>
                 </div>
                  <div className="flex justify-end items-center gap-3">
                        <ReturnBtn/>
                        <Link href="/agent/new-agent/name-agent"><Button className="cursor-pointer flex-1 md:flex-0">مرحله بعد <ArrowLeft/></Button></Link>
                  </div>
               </div>
               
            
            </>
      )
}
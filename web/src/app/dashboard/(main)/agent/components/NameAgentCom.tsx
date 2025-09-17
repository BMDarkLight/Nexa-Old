"use client"
import React from "react";
import ReturnBtn from "./ReturnBtn";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import RedirectBtn from "./RedirectBtn";
import { useAgent } from "@/app/dashboard/context/AgentsContext";
import { useRouter } from "next/navigation";
import Cookie from "js-cookie";
const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = "/agents";
export default function NameAgentCom(){
      const {agent , setField} = useAgent();
      const router = useRouter();
      console.log(agent);
      
const handleSave = async () => {
    try {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type");
      const res = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
        } ,
        body: JSON.stringify(agent),
      });

      if (!res.ok) {
        const data = await res.json()
        console.log(data.detail); 
      }
      router.push("/agent"); 
    } catch (error) {
      console.error(error);
      console.log(error);
    }
  };
      return(
            <>
                <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
                 <div className="flex flex-col gap-5">
                   <h2 className="text-xl font-medium mt-5 md:mt-0">اطلاعات ایجنت را وارد کنید</h2>
                  <div className="w-full md:w-[80%]">
                        <Label htmlFor="name-agent" className="mb-3">نام ایجنت</Label>
                      <Input  id="name-agent" type="text" placeholder="نام ایجنت" value={agent.name} onChange={(e)=> setField("name" , e.target.value)}/>     
                  </div>
                 </div>
                  <div className="flex justify-end items-center gap-3">
                        <ReturnBtn/>
                        <Button className="cursor-pointer flex-1 md:flex-0" onClick={handleSave}>ذخیره<Check/></Button>
                                    
                  </div>
               </div>
            
            </>
      )
}
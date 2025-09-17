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
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
export default function ConnectorCard(){
      return(
            <>
               <div className="flex flex-col gap-5 lg:px-5">
                  <h2 className="text-xl font-medium sm:mt-5 md:mt-0">افزودن اتصالات</h2>
                  <div className="flex justify-between flex-wrap gap-5 lg:grid lg:grid-cols-3 lg:gap-2">
                        <Card className="w-full">
                 <div className="flex ">
                  <div>
                        <picture>
                              <img src="/Squad/image/card-img.png" className="w-10" alt="" />
                        </picture>
                  </div>
                 <div className="mr-3 w-full">
                   <CardHeader>
                     <CardTitle className="text-sm font-semibold">گوگل شیت </CardTitle>
                </CardHeader>
            <CardContent className="text-xs">
                 <p>جدول‌های گوگل شیت خود را تحلیل کنید.</p>
           </CardContent>
           <div className="flex justify-end mt-3">
            <CardFooter>
             <Button className="cursor-pointer"><ArrowLeft /></Button>
       </CardFooter>
           </div>
                 </div>
                 </div>
       

            </Card>
             <Card className="w-full">
                 <div className="flex ">
                  <div>
                        <picture>
                              <img src="/Squad/image/card-img.png" className="w-10" alt="" />
                        </picture>
                  </div>
                 <div className="mr-3 w-full">
                   <CardHeader>
                     <CardTitle className="text-sm">گوگل شیت </CardTitle>
                </CardHeader>
            <CardContent className="text-xs">
                 <p>جدول‌های گوگل شیت خود را تحلیل کنید.</p>
           </CardContent>
           <div className="flex justify-end mt-3">
            <CardFooter>
             <Button className="cursor-pointer"><ArrowLeft /></Button>
       </CardFooter>
           </div>
                 </div>
                 </div>
       

            </Card>
                  </div>
               </div>
            </>
      )
}
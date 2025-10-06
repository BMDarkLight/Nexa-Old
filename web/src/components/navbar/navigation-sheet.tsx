"use client"
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Menu } from "lucide-react";
import { Logo } from "./logo";
import { NavMenu } from "./nav-menu";
import Link from "next/link";
import { Spinner } from "@/components/ui/spinner";
import { useRouter } from "next/navigation";
import { useState } from "react";

export const NavigationSheet = () => {
  const router = useRouter()
    const [loading , setLoading] = useState(false);
  
    const handleLoading = async ()=>{
       setLoading(true)
       requestAnimationFrame(()=>{
        router.push("/login")
       })
  
       setTimeout(()=> setLoading(false) , 1500)
    }
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="icon" className="rounded-full">
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent side="top" dir="rtl" className="p-2">
        <Logo />
        <div className="flex justify-center items-center w-full mt-12">
          <NavMenu orientation="vertical" />
        </div>

        <div className="mt-8 space-y-4 flex gap-3">
          <Button variant="outline" className="sm:hidden flex-1 rounded-full" onClick={handleLoading} disabled={loading}>
            {loading ? <Spinner /> : "ورود"}
          </Button>
          <Button className="text-sm rounded-full xs:hidden">رایگان امتحان کنید</Button>
        </div>
      </SheetContent>
    </Sheet>
  );
};

import React from "react";
import {cn} from "@/lib/utils";
function LoginStructure({children,}: Readonly<{ children: React.ReactNode; }>){
    return(
        <>
            <div className="bg-background flex min-h-svh flex-col items-center justify-center gap-6 p-6 md:p-10" dir="rtl">
                <div className="w-full max-w-sm">
                    <div className={cn("flex flex-col gap-6")}>
                         {children}
                       
                    </div>
                </div>
            </div>
        </>
    )
}
export default LoginStructure;
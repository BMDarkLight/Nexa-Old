import React from "react";
type TLoginHeader = {
    title : string ;
    subTitle : string ;
    headerLink : string | null ;

}
export default function LoginHeader({title , subTitle , headerLink} : TLoginHeader){
    return(
        <>
            <div className="flex flex-col items-center gap-2">
                {/* Logo Image */}
                <a
                    href="#"
                    className="flex flex-col items-center gap-2 font-medium"
                >
                    <div className="flex size-8 items-center justify-center rounded-md">
                        <picture>
                            <img src="/Squad/Login/Logo.png" alt=""/>
                        </picture>
                    </div>
                </a>
                <h1 className="text-xl font-bold">{title}</h1>
                <div className="text-center text-sm">
                    {subTitle}{" "}
                    <a href="#" className="underline underline-offset-4">
                        {headerLink}
                    </a>
                </div>
            </div>
        </>
    )
}

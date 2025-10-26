import React from "react";
interface IHeaderProp{
      title : string ;
      text : string ;
}
export default function Header({title , text} : IHeaderProp){
      return(
            <>
            <div className="mt-4 border-b-1 pb-5 hidden md:block">
                  <h2 className="font-bold text-2xl">{title}</h2>
                  <p className="mt-1 text-base text-[#71717A]">{text}</p>
            </div>
            
            </>
      )
}

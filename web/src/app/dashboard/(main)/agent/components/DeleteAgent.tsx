"use client"
import React, { useState } from "react";
import { Bot, EllipsisVertical, Plus, Trash2 } from "lucide-react";
import Swal from "sweetalert2";
import Cookie from "js-cookie";
import { useRouter } from "next/navigation";
type TAgentDelete = {
      id : string
      onDelete : (id : string)=> void
}
const API_Base_Url = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000"
const End_point = process.env.NEXT_PUBLICK_ENDPOINT = "/agents"
export default function DeleteAgent({id , onDelete} : TAgentDelete){
      const router = useRouter()
      const [show , setShow] = useState(false);
      const handleDeleteAgent = async ()=>{
            const result = await Swal.fire({
                  title : "حذف ایجنت" ,
      text: "آیا مطمئن هستید که می‌خواهید ایجنت فلان را حذف کنید؟",
      showCancelButton: true,
      cancelButtonText: "انصراف",
      confirmButtonText: "خروج",
      reverseButtons : true ,
      customClass : {
        popup : "swal-rtl" ,
        title : "swal-title" , 
        confirmButton : "swal-confirm-btn swal-half-btn" , 
        cancelButton : "swal-cancel-btn swal-half-btn" ,
        htmlContainer : "swal-text" , 
        actions : "swal-container"
      }
            })

            if(result.isConfirmed){
                  try{
                        const token = Cookie.get("auth_token")
                        const token_type = Cookie.get("token_type")
                        const response = await fetch(`${API_Base_Url}${End_point}/${id}` , {
                              method: "DELETE" , 
                              headers:{
                                    Authorization: `${token_type} ${token}`
                              }
                        })
                        if(response.ok){
                              if(onDelete) onDelete(id);
                        } else{
                              const data = await response.json()
                              console.log(data.detail);
                        }
                  }catch(err){
                        console.log(err);  
                  }
            }
            setShow(!show)
      }
      return(
            <>
                <div className=" absolute top-0 right-[90%] cursor-pointer">
                              <EllipsisVertical size={20} onClick={()=>setShow(!show)} />
                              <div className={`flex justify-between items-center w-40 rounded-md px-2 py-2  absolute top-[-35px] left-[2px] bg-white shadow-md hover:text-[#DC2626] transition duration-400 ${show ? `block` : `hidden`}`} onClick={handleDeleteAgent}>
                                    <p className="text-sm">حذف</p>
                                    <Trash2 size={16} />
                              </div>
                        </div>
            
            
            </>
      )
}
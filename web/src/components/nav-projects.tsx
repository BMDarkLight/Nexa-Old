"use client"

import {
  Folder,
  Forward,
  MoreHorizontal,
  Trash2,
  type LucideIcon,
} from "lucide-react"

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import Link from "next/link"
import { usePathname } from "next/navigation"
import Swal from "sweetalert2"
import { cn } from "@/lib/utils"
import Cookie from "js-cookie"
export function NavProjects({
  projects,
}: {
  projects: {
    name: string
    url: string
    icon: LucideIcon
    color?: string
    type?: string
    hasChild?: boolean
  }[]
}) {
  const { isMobile } = useSidebar()
  const pathname = usePathname()
  const handleLogout = async ()=>{
    const result = await Swal.fire({
      title : "خروج از حساب" ,
      text: "آیا مطمئن هستید که می‌خواهید از حساب کاربری خود خارج شوید؟",
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
      Cookie.remove("auth_token")
      Cookie.remove("token_type")
      window.location.href = "/login"
    }
  }
  const handleWalet = async ()=>{
    const result = await Swal.fire({
              title: "اعتبار فعلی",
              html: `
              <div>
                 <div style="margin-bottom: 0.5rem ;">اعتبار فعلی شما 12,000,000 تومان می باشد</div>
                 <div>برای افزایش اعتبار با 09105860050 تماس بگیرید</div>
              </div>
              
              `,
              showConfirmButton: false,
              showCancelButton: false,
              showCloseButton: true,
              customClass: {
                popup: "swal2-rtl",
                title: "swal-title",
                htmlContainer: "swal2-text",
              },
            });

  }
  return (
    <SidebarGroup className="group-data-[collapsible=icon]:hidden">
      <SidebarMenu>
        {projects.map((item) => ( 
          item.type == "link" ? (
          <SidebarMenuItem key={item.name}>
          
            <SidebarMenuButton asChild className={cn(pathname.startsWith(item.url) ? `bg-primary/50 text-[#001120] hover:bg-primary/70 hover:text-[#001120]` : ``)}>
              <Link href={item.url}>
                <item.icon className={item.color}/>
                <span >{item.name}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          ) : (
            <SidebarMenuItem key={item.name}>
            <SidebarMenuButton asChild onClick={()=>{
              if(item.type == "action"){
                handleLogout();
              }else if(item.type == "alert"){
                handleWalet()
              }
            }}>
              <Link href={item.url}>
                <item.icon className={item.color}/>
                <span >{item.name}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          )
        ))} 
      </SidebarMenu>
    </SidebarGroup>
  )
}

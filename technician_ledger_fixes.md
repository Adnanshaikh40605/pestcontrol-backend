PestControl99 Software – Technician Ledger Logic, Requirements & Errors
A. Technician Ledger – Main Logic
Technician Ledger report mein har technician ka complete work aur payment record show hona chahiye.

Har entry ka status clearly Settled / Unsettled dikhna chahiye.

Isi report se hum select kar sakein ki kaunsi booking/service ka technician payment settle karna hai aur kitna amount settle kiya gaya hai.

Payment / Share Logic
1. One-Time Booking

Technician share = Booking Amount ka 40%
Service complete hone ke baad full 40% settlement ke liye available hoga.
2. AMC Booking

AMC ka 40% share full booking amount par ek saath settle nahi hoga.
Settlement per completed service/visit ke hisab se hoga.
Example: ₹3,000 AMC mein 3 services hain:
Per Service Value = ₹1,000
Technician Share Per Service = ₹400 (40%)
Har service complete hone ke baad concerned technician ke ledger mein ₹400 settlement ke liye show hona chahiye.
Important: AMC ki har service same technician kare, ye zaroori nahi hai.

Example:

Service 1 – Akshay → Akshay ko us service ka 40%
Service 2 – Rahul → Rahul ko us service ka 40%
Service 3 – Sameer → Sameer ko us service ka 40%
Jis technician ne jo service complete ki hai, usi technician ke ledger mein us service ka share aana chahiye.

3. Multiple Technicians on Same Service Agar ek booking/service par 2 technicians assign hote hain, to total technician share 40% hi rahega, lekin dono technicians ke beech divide hoga.

Example:

Service Value = ₹1,000
Total Technician Share = ₹400
2 technicians hain to ₹200 + ₹200
Booking/service ki entry dono technicians ke ledger mein show honi chahiye.
 
B. Service-Wise Logic
Cockroach Control – One-Time + AMC
Termite Control – Only One-Time
Bed Bugs – 2 Services
Rodent Control – One-Time + AMC, especially Society/Commercial
Mosquito Control – One-Time + AMC, especially Society/Commercial
System ko service type ke according automatically settlement calculation karna chahiye.

 
C. Technician Ledger Report Requirements
Har ledger entry mein minimum ye details show honi chahiye:

Booking ID
Booking Date
Customer Name
Property Type
Residence / Society / Commercial etc.
Service Name
One-Time / AMC
Service Number, e.g. Service 1 of 3
Total Booking Amount
Current Service Value
Technician Share %
Technician Payable Amount
Assigned Technician(s)
Service Status
Payment Status – Settled / Unsettled
Settlement Date
Settlement Option
Report mein checkbox/select option hona chahiye jisse hum multiple Unsettled entries select karke payment settle kar sakein.

Example:

Selected 8 Services → Total Technician Payable ₹6,450 → Settle Payment

Settlement karne ke baad entry delete ya report se disappear nahi honi chahiye.

Entry same ledger mein rahe aur status:

Unsettled → Settled

ho jaye.

Saath mein settlement date bhi save honi chahiye, taaki future mein complete payment history check kar sakein.

 
D. AMC / Service Call Entry Logic
AMC ke case mein main booking ko baar-baar payment entry nahi banana hai.

Har completed service call ki separate payable entry maintain honi chahiye, kyunki technician settlement per service hoga.

Example:

Booking ID: 2001
AMC Amount: ₹3,000
Total Services: 3

Ledger:

Service 1 → Akshay → ₹400 → Settled
Service 2 → Rahul → ₹400 → Unsettled
Service 3 → Upcoming

Isse clear rahega ki kis service ka payment kis technician ko diya gaya hai.

 
E. Old Service Calls
Old/completed service calls ka record delete nahi hona chahiye.

Same Technician Ledger report mein separate section/filter hona chahiye:

Payment Settlement

Unsettled entries
Settlement History

Already Settled entries
Old Service Calls / History

Previous completed service calls ka complete record
Old settled services ko current payment settlement amount mein include nahi karna hai.

 
F. Current Errors to Fix
1. Technician Share Showing ₹0
Booking ID: 1895

Akshay technician ke ledger mein Prachiti client ki entry ka technician share ₹0 show ho raha hai.

Please check share calculation/assignment logic.

2. Bed Bugs Wrong 40% Calculation
Booking ID: 1925

Bed Bugs mein 2 services hoti hain.

Currently system direct full booking amount ka 40% technician share dikha raha hai.

Correct logic:

Booking Amount ÷ 2 Services × 40% = Technician Share Per Service

Har completed service ka settlement separately hona chahiye.

3. Booking Done But Report Showing Pending
Booking/service ko Done/Completed mark karne ke baad bhi Technician Ledger report mein Pending show ho raha hai.

Booking/service status aur ledger status properly sync hona chahiye.

4. Settlement Option Missing
Technician Ledger report mein payment Settle karne ka option currently nahi dikh raha hai.

Settlement option add karna hai.

Settlement ke baad record remove nahi hona chahiye. Sirf status Settled hona chahiye.

 
G. Customer Booking History Errors
1. Total Revenue Showing Double
Example Customer:

Heena – 8454845141

Actual Booking Amount = ₹3,000

Lekin Customer Booking History mein Total Revenue ₹6,000 show ho raha hai.

System same booking/service amount ko duplicate calculate kar raha hai. Total Revenue mein actual booking amount sirf ek baar count hona chahiye.

2. Termite Upcoming Service Showing Multiple Times
Customer Booking History ke Upcoming Services mein Termite ki entry 6 times show ho rahi hai.

Ye incorrect hai.

Termite = One-Time Service Only

Isliye Termite booking mein AMC/upcoming repeat service automatically create nahi honi chahiye.

Customer Booking History mein Termite ki sirf one booking/service entry show honi chahiye.

 
Final Important Logic
Software ka main rule simple hona chahiye:

Technician ko payment booking ke basis par nahi, uske actually completed service/visit ke basis par milega.

One-Time → Full applicable 40%
AMC → Per completed service 40%
Bed Bugs → 2 services mein divide karke per service 40%
2 technicians → Same 40% share technicians mein divide hoga
Different AMC technicians → Jisne service ki, usi ke ledger mein share
Settled record delete nahi hoga
Complete settlement history maintain hogi
Termite sirf One-Time rahega
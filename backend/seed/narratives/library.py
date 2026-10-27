"""Template library for the synthetic grievance corpus.

All names, institutions, localities and contact details are fictional. Templates
are intentionally written in the register used by students, parents, staff and
officials rather than as polished marketing copy.
"""

PERSONA_OPENERS = {
    "STUDENT": [
        "I am a {year} student of {programme} at {institution}.",
        "I am enrolled in the {sem} semester of {programme} at {institution}.",
        "I am writing as a current student of {institution} ({programme}, {year}).",
    ],
    "PARENT": [
        "I am the parent of a {programme} student at {institution}.",
        "My child is studying in the {sem} semester of {programme} at {institution}.",
        "I am writing on behalf of my child, a {year} student at {institution}.",
    ],
    "FACULTY": [
        "I am a faculty member in the {department} department at {institution}.",
        "I have been teaching in the {department} department of {institution} since {join_year}.",
        "I am a member of the teaching staff at {institution}.",
    ],
    "NON_TEACHING_STAFF": [
        "I work in the administrative section of {institution}.",
        "I am a non-teaching employee of {institution} and wish to place certain facts on record.",
    ],
    "ALUMNUS": [
        "I passed out of {institution} in {pass_year} and am raising a matter concerning current students.",
        "I am an alumnus of the {programme} programme of {institution}.",
    ],
    "ANONYMOUS_WELLWISHER": [
        "I am a well-wisher of the students of {institution} and do not wish to disclose my identity.",
        "I am sending this complaint anonymously because I fear that my name will become public.",
    ],
    "ADVOCATE_ON_BEHALF": [
        "I am an advocate appearing on behalf of a group of students of {institution}.",
        "This complaint is filed on behalf of my clients, who are students of {institution}.",
    ],
    "STUDENT_ASSOCIATION": [
        "I am writing on behalf of the students' association of {institution}.",
        "The students' association of {institution} has received repeated representations on this issue.",
    ],
    "MINISTRY_REFERENCE": [
        "This reference has been received from the Ministry of Education for necessary action.",
        "The Ministry has forwarded the enclosed representation from a student of {institution}.",
    ],
    "MP_MLA_REFERENCE": [
        "This representation has been forwarded by a public representative on behalf of students of {institution}.",
        "The matter was raised before a public representative and has been forwarded for examination.",
    ],
    "COURT_DIRECTION": [
        "The matter is placed before AICTE pursuant to a direction of the Hon'ble High Court in a writ petition filed by students of {institution}.",
        "This office has received a court direction requiring a factual report in respect of {institution}.",
    ],
    "AICTE_INTERNAL": [
        "A routine file review of {institution} has brought out the following discrepancy.",
        "The Expert Visit Committee observations in respect of {institution} require a fresh examination.",
        "This note is placed on file on the basis of the approval verification exercise for {institution}.",
    ],
    "REGIONAL_OFFICE_REPORT": [
        "A complaint was received at the Regional Office on {date} concerning {institution}.",
        "The Regional Office has received a representation against {institution} and forwards the factual position below.",
    ],
}

TRY_LINES = [
    "I met the Principal on {date} and submitted a written representation; no acknowledgement was given.",
    "I mailed the college office on {date} and again on {date2}, but no reply has been received.",
    "We approached the Head of Department, who said the matter was beyond his control.",
    "The students' association raised the issue with the management in a meeting held on {date}.",
    "I sent a registered letter to the institution on {date}; the postal acknowledgement is enclosed.",
    "A representation was submitted to the grievance cell of the institution on {date} but it was not diarised.",
    "I requested the accounts section for a copy of the receipt, but was told that records were not available.",
    "We were assured at the admission counter that the amount was refundable, but the assurance was not honoured.",
]

FEAR_LINES = [
    "I am afraid to give my full name because my internal marks are still pending.",
    "The students who have complained earlier were told that their attendance would be marked short.",
    "I am writing anonymously as I fear retaliation during the forthcoming examination.",
    "My parents have asked me not to pursue the matter, but I believe it should be examined.",
    "Please keep my identity confidential; the institution is aware of my hostel room number.",
]

ASK_LINES = {
    "FEE": [
        "Kindly direct the institution to refund the excess amount along with a clear fee breakdown.",
        "I request AICTE to verify the fee notification and direct the college to issue a proper receipt.",
        "Kindly cause an inquiry into the fee collection and ensure that original documents are released.",
    ],
    "FACULTY": [
        "Kindly verify the faculty position shown on the AICTE portal and direct the institution to appoint qualified faculty.",
        "I request an inspection of the department and suitable action for the faculty shortage.",
        "Kindly direct the institution to regularise the salary and service conditions of the affected staff.",
    ],
    "INFRASTRUCTURE": [
        "Kindly direct an inspection of the laboratories, hostel and fire safety arrangements.",
        "I request AICTE to obtain a factual report from the institution and ensure minimum standards are met.",
        "Kindly direct the institution to provide the facilities promised at the time of admission.",
    ],
    "APPROVAL_VIOLATION": [
        "Kindly verify the approved intake and programme list and take action against the excess admissions.",
        "I request AICTE to examine the approval status and direct the institution to stop unauthorised admissions.",
        "Kindly cause the records of admission and approval to be compared and appropriate action taken.",
    ],
    "ACADEMIC_ADMINISTRATION": [
        "Kindly direct the institution to declare the result and provide the marks statement without further delay.",
        "I request AICTE to examine the internal assessment records and ensure fair treatment of students.",
        "Kindly direct the institution to issue the migration certificate as per the applicable rules.",
    ],
    "RAGGING_DISCRIMINATION": [
        "Kindly ensure a discreet inquiry and appropriate protective measures for the affected students.",
        "I request AICTE to direct the institution to activate its anti-ragging committee and report action taken.",
        "Kindly ensure that the complainants are not identified and that counseling support is provided.",
    ],
    "GOVERNANCE_MISCONDUCT": [
        "Kindly cause an inquiry into the financial and administrative irregularities and fix responsibility.",
        "I request AICTE to obtain the relevant records and take appropriate regulatory action.",
        "Kindly direct a special audit or inspection of the institution and place the findings on record.",
    ],
    "OTHER": [
        "Kindly direct the institution to examine the grievance and communicate a decision to the complainant.",
        "I request AICTE to forward the matter to the appropriate authority for early action.",
    ],
}

SHORT_TEMPLATES = {
    "FEE": [
        "Excess fee of Rs. {amount} was charged for {programme} at {institution}. Receipt no. {receipt} was not given. Kindly intervene.",
        "The college is not refunding Rs. {amount} after withdrawal from {programme}. Admission was cancelled on {date}. Please direct refund.",
        "My original certificates are held by {institution} for non-payment of an disputed charge of Rs. {amount2}. Kindly help.",
    ],
    "FACULTY": [
        "Faculty shortage in {department} at {institution} is affecting classes. Kindly verify the AICTE portal data.",
        "Salary for {month} has not been paid to several faculty members at {institution}. No written reply is being given.",
        "A faculty member shown as working at {institution} has not attended classes this semester. Please inquire.",
    ],
    "INFRASTRUCTURE": [
        "The {lab} laboratory at {institution} has no working equipment. Practical classes are being conducted only on paper.",
        "Hostel and mess conditions at {institution} are unhygienic and unsafe. Kindly send an inspection team.",
        "There is no valid fire NOC for the {building} block of {institution}. Students are worried about safety.",
    ],
    "APPROVAL_VIOLATION": [
        "Admissions have been made beyond the approved intake in {programme} at {institution}. Please verify the sanctioned strength.",
        "The college is advertising an unapproved {programme} course for {year}. Kindly take action.",
        "A second shift is being run at {institution} without approval. The admission brochure is attached.",
    ],
    "ACADEMIC_ADMINISTRATION": [
        "Results for the {sem} semester at {institution} have not been declared since {date}. Students are unable to apply for internships.",
        "Internal marks of {programme} students were changed without showing answer scripts at {institution}. Please inquire.",
        "The college is refusing to issue a migration certificate despite completion of {programme}. Kindly direct issuance.",
    ],
    "RAGGING_DISCRIMINATION": [
        "Some students at {institution} are being harassed by senior students in the hostel and are afraid to attend classes. Kindly inquire discreetly.",
        "A group of students at {institution} is facing discriminatory remarks from staff. We request a confidential inquiry.",
    ],
    "GOVERNANCE_MISCONDUCT": [
        "Fee collections at {institution} are not being deposited in the official account. Kindly cause an audit.",
        "The management of {institution} is using fake documents for approval. A copy of the discrepancy is enclosed.",
    ],
    "OTHER": [
        "The bus fee at {institution} was increased without notice and students are being denied transport. Kindly look into it.",
        "Scholarship amount for {year} has not been credited to students of {institution}. No reply is being given.",
    ],
}

CORE_TEMPLATES = {
    "FEE": {
        "EXCESS_FEE": [
            "At the time of admission to {programme} for the academic year {year}, the institution collected Rs. {amount} against the notified fee of Rs. {amount2}. The difference was described as a 'development fund' at the counter, although no such head appears in the fee notification. The payment was made through UPI reference {utr} on {date}, and the receipt issued merely says 'miscellaneous'. Several students in the same batch have been charged different amounts.",
            "The fee structure displayed on the institution's notice board for {programme} for {year} shows a total of Rs. {amount2}, but the accounts section insisted on Rs. {amount}. When I asked for the break-up, I was told that the extra amount was for 'accreditation charges' and that no separate receipt would be issued. I have enclosed the demand slip and the bank statement showing the transfer.",
            "My admission to {programme} was confirmed on {date} after payment of Rs. {amount}. Subsequently the institution demanded a further Rs. {amount2} before the commencement of the {sem} semester, failing which my registration would not be confirmed. The original fee notification does not mention this charge. Other students from {city} have received similar demands.",
        ],
        "REFUND_NOT_GIVEN": [
            "I was admitted to {programme} at {institution} for {year} and paid Rs. {amount} on {date}. I withdrew from the programme on {date2} before the cut-off date mentioned in the admission letter and submitted a written cancellation request along with the original receipt. The institution has neither refunded the amount nor communicated any decision, despite the refund policy printed in the prospectus.",
            "After my admission to {programme}, I cancelled the seat on {date} because of a family emergency and joined another institution. The college retained the entire fee of Rs. {amount}, although only a small processing fee is permitted. I have visited the accounts office four times and written to the Principal, but the only response is that the 'management will decide'.",
            "The admission letter stated that fees would be refunded after deduction of Rs. {amount2} if withdrawal was made before {date}. I complied with the condition, but {institution} has not processed the refund of Rs. {amount}. The administrative officer stopped responding after I asked for the calculation in writing.",
        ],
        "DOCUMENTS_WITHHELD": [
            "I completed {programme} at {institution} in {year}, but my original Class XII certificate and migration certificate are still with the college. The office says the documents will be released only after payment of Rs. {amount}, which is described as an 'outstanding activity fee'. I was not informed of this charge at the time of admission and no receipt has been shown to me.",
            "Although I have cleared all academic dues, {institution} is refusing to return my original documents. The records section has kept the certificates on the ground that a 'caution deposit' of Rs. {amount} remains unpaid. The caution deposit was already adjusted against the hostel charges, for which a receipt is available.",
            "My daughter's original certificates were submitted at the time of admission to {programme} in {year}. She has now completed the course, but the college is holding the documents because of an alleged unpaid fee of Rs. {amount}. We have requested a written statement of dues but have not received any reply.",
        ],
        "HIDDEN_CHARGES": [
            "The prospectus for {programme} for {year} mentions a consolidated fee of Rs. {amount}, but at the time of admission {institution} collected Rs. {amount2} in cash towards 'caution money', 'development charges' and 'industry interaction'. None of these heads appear in the approved fee structure. When parents objected, the staff said the amount was compulsory for all students.",
            "In addition to the notified tuition fee, {institution} has been collecting Rs. {amount} per semester under the head 'academic support services'. No receipt is issued for this amount and the fee notification displayed at the counter does not mention it. Students who question the charge are told that their internal marks may be affected.",
            "At the time of admission to {programme}, we paid the fee shown in the notification. Later the institution demanded Rs. {amount} for a 'mandatory soft skills programme' and Rs. {amount2} for 'library development', although both facilities are already covered by the regular fee. The demands were made by circular without any approval reference.",
        ],
        "CASH_WITHOUT_RECEIPT": [
            "The accounts counter at {institution} demanded Rs. {amount} in cash for the {sem} semester fee and refused to accept UPI or cheque. No receipt was issued, and the entry in the register was made only after I insisted. Another parent who paid at the same counter was also not given a receipt. I am enclosing a photograph of the counter notice, which does not display any fee head.",
            "I paid Rs. {amount} in cash towards the examination fee at {institution} on {date}. The clerk took the money and wrote a token number on a slip of paper, saying the official receipt would be sent by email. No receipt has been received after {days} days, and the examination form still shows the fee as unpaid.",
            "Although the institution's notice says all payments must be made online, the hostel office at {institution} collected Rs. {amount} in cash for mess charges. No receipt was given and the amount was not reflected in the portal. Several students have faced the same problem but are afraid to complain.",
        ],
    },
    "FACULTY": {
        "SALARY_UNPAID": [
            "I have been working as an Assistant Professor in the {department} department of {institution} since {join_year}. My salary for {month} has not been paid, and the salary for the previous month was short by Rs. {amount}. The accounts section says the bank account is under verification, but no written communication has been issued. Several colleagues are affected.",
            "Faculty members in the {department} department at {institution} have not received full salary for the last {days} days. The management has been deducting an amount of Rs. {amount} under 'administrative charges' without any appointment order or consent. When we asked for the calculation, we were told to sign a fresh undertaking.",
            "I joined {institution} as a faculty member in {join_year} on a consolidated salary of Rs. {amount}. For the last three months, only part of the amount has been credited. The Principal has verbally assured payment but no date has been given. My family is dependent on this income and I request AICTE to examine the service conditions.",
        ],
        "GHOST_FACULTY": [
            "The faculty list displayed for {institution} on the AICTE portal shows {staff} as a full-time professor in the {department} department. However, this person has not attended the department during the current semester. Classes are being adjusted by guest lecturers while the attendance register is being signed in the name of the absent faculty member.",
            "Several names shown against {institution} in the AICTE portal do not correspond to persons actually working on campus. In the {department} department, two faculty members are shown as full-time, but students have not seen them since the beginning of {year}. The institution is using their names to satisfy the faculty ratio requirement.",
            "The college claims to have {faculty_count} faculty members in {programme}, but only a few are present on working days. Some of the names on the notice board are of retired teachers who visit only for signatures. I request a surprise verification of the faculty position.",
        ],
        "FORCED_RESIGNATION": [
            "I am a faculty member in the {department} department of {institution}. I was asked to submit my resignation on {date} without any prior notice or inquiry. When I refused, my access to the staff portal was blocked and my salary was withheld. The management has been pressuring other faculty members to sign resignation letters in blank.",
            "After I raised concerns about the faculty shortage at {institution}, I was transferred to a different department and then asked to resign. The letter given to me cites 'administrative reasons' but no specific allegation. I have served the institution for {years} years and my service record is clean.",
            "Several faculty members at {institution} have been forced to resign after they questioned the management's use of funds. The resignations were obtained under threat of withheld salary and adverse experience certificates. I am submitting this complaint with the request that the matter be examined confidentially.",
        ],
        "QUALIFICATION_NOT_AS_PER_NORMS": [
            "The {department} department at {institution} is being run by faculty members who do not possess the qualifications prescribed by AICTE. One of them has only a bachelor's degree in a related subject but is shown as a professor. Students in {programme} are being taught core subjects by such faculty.",
            "According to the AICTE norms for {programme}, the faculty should have a postgraduate degree in the relevant discipline. At {institution}, several faculty members are from unrelated disciplines and some have not completed the required certification. The institution's website nonetheless claims that all faculty are AICTE-qualified.",
            "The institution has appointed faculty on ad-hoc contracts without verifying their degrees. In the {department} department, at least two faculty members have submitted documents that do not match the university records. I request verification of the original certificates and the approval status.",
        ],
        "FACULTY_STUDENT_RATIO": [
            "The sanctioned intake for {programme} at {institution} is {intake}, but the actual number of students in the {sem} semester is much higher. The department has only a few regular faculty members, and the faculty-student ratio is far below the prescribed norm. Lectures are being held in shifts and practical batches are overcrowded.",
            "Although {institution} claims to maintain the required faculty-student ratio, the {department} department has one faculty member handling multiple sections. Students are unable to get doubt-clearing time and internal assessments are being conducted without adequate teaching. An inspection at short notice will reveal the position.",
            "The college has increased admissions in {programme} without appointing additional faculty. In the {department} department, the same teacher is shown against several subjects and sections. This is affecting the quality of instruction and is a violation of the approval conditions.",
        ],
    },
    "INFRASTRUCTURE": {
        "LAB_WITHOUT_EQUIPMENT": [
            "The {lab} laboratory at {institution} does not have working equipment for the practical syllabus of {programme}. Students are being asked to copy experiments from manuals without performing them. The few available instruments are either damaged or kept locked. This has been the position since the beginning of the {sem} semester.",
            "Practical classes for {programme} at {institution} are being conducted in a room that has no functional lab equipment. The college claims on its website that the laboratory was upgraded in {year}, but the equipment list displayed on the wall is outdated. Parents have raised the issue repeatedly without any improvement.",
            "The computers in the {lab} laboratory at {institution} are not in working condition and the software required for the {sem} syllabus is not installed. Students are paying a laboratory fee of Rs. {amount} but receiving only theoretical demonstrations. Kindly arrange an inspection of the facility.",
        ],
        "LIBRARY_DEFICIENT": [
            "The library at {institution} does not have the prescribed books and journals for {programme}. Students are unable to prepare for the {sem} examinations because the reference copies are either missing or outdated. The reading room is also used for storing furniture, leaving very little space for students.",
            "Although the institution advertises a digital library, the computers in the library at {institution} have no working internet connection. The number of books available for the {department} department is far below the requirement. Several students have purchased books at their own cost because the library could not provide them.",
            "The library timings at {institution} are restricted to a few hours and the collection does not cover the current syllabus. When students requested additional copies, the librarian said there was no budget. The library fee of Rs. {amount} is still being collected from every student.",
        ],
        "HOSTEL_MESS_CONDITIONS": [
            "The hostel and mess at {institution} are in poor condition. The water supply is irregular, the toilets are not cleaned regularly, and the food served is of poor quality. Several students have fallen ill during the {sem} semester. The hostel warden has been informed in writing but no corrective action has been taken.",
            "My child is staying in the hostel at {institution}. The rooms are overcrowded and the mess is serving food in unhygienic conditions. Despite paying Rs. {amount} per semester, the basic facilities promised in the hostel brochure are not available. We are worried about the health and safety of the students.",
            "The hostel at {institution} has no proper ventilation and the fire exit is blocked by stored furniture. The mess contractor changes frequently and the quality of food varies from day to day. Students who complain are told that they can leave the hostel if they are not satisfied.",
        ],
        "BUILDING_SAFETY": [
            "A portion of the {building} block at {institution} is being used for classes despite visible cracks in the walls and ceiling. During the last inspection by the local authority, a portion was marked unsafe. The institution has not shifted the classes or obtained a structural stability certificate.",
            "Students at {institution} are attending classes in a building that has no proper staircase lighting and only one narrow exit. In an emergency, evacuation would be difficult. The institution has been informed about the condition, but no repair work has been undertaken.",
            "The {building} block of {institution} was constructed without the required setback and has no occupancy certificate. Classes are being held on the upper floors even though the lift is frequently out of order. We request an urgent safety inspection.",
        ],
        "NO_FIRE_NOC": [
            "The {building} block of {institution} does not have a valid fire NOC. Fire extinguishers are either missing or past their expiry date, and the emergency exit is locked during class hours. This is a serious safety concern for students and staff.",
            "Although the institution's website claims that fire safety norms are complied with, no fire NOC is displayed on the premises of {institution}. The staircases are narrow and the assembly area is used for parking. Kindly inspect the campus and direct compliance.",
            "During a recent fire safety drill at {institution}, it was found that the alarms in the {building} block were not working. The institution has not produced a current fire NOC despite repeated requests from the student association.",
        ],
        "NO_PLAYGROUND": [
            "The land shown as a playground in the approved layout of {institution} has been converted into a parking area. Students of {programme} have no space for sports or physical education. The institution continues to collect an annual sports fee of Rs. {amount}.",
            "Despite the approved plan showing a playground, {institution} has constructed a new block on the open ground. The students are forced to use the road outside the campus for sports activities. This is a violation of the approval conditions.",
            "There is no playground or sports facility at {institution}. The physical education period is used for other classes and the sports equipment is not available. The institution should be asked to provide the facility promised in its approval documents.",
        ],
    },
    "APPROVAL_VIOLATION": {
        "BEYOND_INTAKE": [
            "For the academic year {year}, {institution} admitted more students in {programme} than the sanctioned intake of {intake}. The excess admissions were made after the last date and without any approval. The admission list displayed on the notice board does not match the number of students attending classes.",
            "The approved intake for {programme} at {institution} is {intake}, but the first-year classrooms currently have more than {actual_intake} students. Several students were admitted against management quota seats that are not reflected in the approval. The institution is collecting full fees from these students without any valid seat allotment.",
            "I am a student of {programme} at {institution}. At the time of admission, we were told that the intake was {intake}, but the college later admitted additional students. The excess students are attending classes in the same sections and there are not enough faculty members or laboratories for everyone.",
        ],
        "UNAPPROVED_PROGRAMME": [
            "{institution} is running a {programme} course that does not appear in its current AICTE approval. The course is being advertised on the institution's website and admissions are being made through a separate application form. Students who joined the course have been told that approval is 'under process'.",
            "The prospectus of {institution} advertises a {programme} programme for {year}, but the course is not approved by AICTE. The institution is collecting a fee of Rs. {amount} from students admitted to this programme. Kindly verify the approval status and take action.",
            "A new {programme} course has been started at {institution} without the required approval or affiliation. Classes are being held in the evening and the faculty members have not been appointed as per norms. The admission brochure claims that the course is AICTE-approved.",
        ],
        "FALSE_APPROVAL_CLAIM": [
            "The advertisement issued by {institution} for {year} states that all programmes are approved by AICTE and that the institution has an 'A' grade. The approval letter displayed at the reception covers only certain programmes and has expired. Prospective students are being misled by the claim.",
            "The website of {institution} displays the AICTE logo and claims approval for {programme}, although the current approval does not cover that programme. Several parents relied on this claim while paying the admission fee of Rs. {amount}. Kindly direct the institution to correct the advertisement.",
            "{institution} has been circulating a brochure that shows an approval number different from the one on the AICTE portal. The brochure also claims accreditation that the institution does not have. This appears to be a deliberate attempt to mislead students during admissions.",
        ],
        "LAPSED_APPROVAL": [
            "The AICTE approval for {institution} lapsed in {year}, but the institution continued to admit students to {programme} for the subsequent academic year. The students were not informed about the lapse. The institution is still displaying the old approval certificate on its notice board.",
            "Although the institution's approval was not renewed after {year}, classes for {programme} are being conducted as usual. The management has told students that the renewal is a formality. We request AICTE to clarify the status and protect the interests of the students.",
            "The approval status of {institution} on the AICTE portal shows that the institution is not approved for the current year, yet admissions are being made for {programme}. The fee of Rs. {amount} is being collected in advance. Kindly cause an immediate verification.",
        ],
        "SECOND_SHIFT": [
            "{institution} is running a second shift for {programme} without obtaining the required approval. The second shift classes are held after 5 pm and the same faculty members are shown for both shifts. The arrangement is not reflected in the approval documents.",
            "A second shift was started at {institution} for {programme} in {year} without any additional intake approval. Students in the second shift do not have access to the library or laboratory after regular hours. The institution is collecting the same fee as the first shift.",
            "The second shift at {institution} is being run in a separate building that is not part of the approved campus. The faculty members are not available for consultation and the classes are often combined with the first shift. Kindly examine the approval conditions.",
        ],
        "AFFILIATION_ISSUE": [
            "{institution} is admitting students to {programme} even though the programme is not affiliated to the university for the current academic year. The university has not granted affiliation and the examination forms are being withheld. Students are worried about the validity of their degree.",
            "The affiliation of {institution} for {programme} expired in {year}, but the institution continued admissions. The university has not approved the syllabus or examination schedule. Parents have been assured that the matter will be resolved, but no written confirmation has been provided.",
            "Although the institution is approved by AICTE, the {programme} course is not affiliated to the university. The college is conducting examinations internally without university approval. This may affect the recognition of the degree.",
        ],
    },
    "ACADEMIC_ADMINISTRATION": {
        "EXAM_RESULT_DELAY": [
            "The results of the {sem} semester examination for {programme} at {institution} have not been declared even after {days} days from the last paper. Students are unable to apply for internships or higher studies. The examination cell has not given any revised date.",
            "Internal assessment marks for {programme} were to be displayed on {date}, but the college has not published them. When students approached the examination section, they were told that the data was being verified. The delay is affecting scholarship applications.",
            "The university has already declared the results for other colleges, but {institution} has not forwarded the marks of our batch. The examination coordinator is not responding to emails. We request AICTE to direct the institution to complete the process.",
        ],
        "INTERNAL_MARKS_MISUSE": [
            "The internal marks of several students in {programme} at {institution} were changed after the answer scripts were shown. Students who questioned the change were told that the moderation committee had decided it. No revised marks statement or calculation sheet has been provided.",
            "At {institution}, internal marks are being used to pressure students who raise grievances. In the {department} department, students who complained about faculty shortage received unexpectedly low internal marks. The answer scripts were not shown despite repeated requests.",
            "The internal assessment records for {sem} at {institution} do not match the marks displayed on the portal. When we asked for the attendance and assignment records, the faculty member refused to provide them. We request an independent verification.",
        ],
        "ATTENDANCE_THREAT": [
            "I was absent for a few days in {sem} due to a documented medical condition. The institution is threatening to detain me for attendance shortage without considering the medical certificate. Other students with similar absences have been treated differently.",
            "The attendance portal of {institution} shows incorrect figures for {programme} students. Several classes that were actually held are not reflected, while some cancelled classes are marked as conducted. Students are being told that they will not be allowed to appear for exams.",
            "Although I attended all classes, my attendance at {institution} has been shown as short because the biometric system was not working. The college is refusing to correct the record unless a fine of Rs. {amount} is paid. Kindly direct a verification of the attendance register.",
        ],
        "PLACEMENT_FALSE_CLAIM": [
            "The placement brochure of {institution} claims that {placement_pct}% of {programme} students were placed with packages up to Rs. {amount}. Several students from the batch have not received any offer, and the companies named in the brochure did not conduct interviews on campus.",
            "During admission, {institution} promised a dedicated placement cell and guaranteed internships. In the final year, no placement drive has been organised and the cell is not responding. The fee for 'placement training' of Rs. {amount2} was collected separately.",
            "The institution's website shows photographs of a placement drive that did not take place for our batch. Students who asked for the list of recruiters were told that the information was confidential. We request AICTE to verify the placement claims.",
        ],
        "MIGRATION_CERTIFICATE": [
            "I completed {programme} at {institution} in {year} and have cleared all dues, but the institution is not issuing my migration certificate. The office says the certificate will be issued only after payment of Rs. {amount} towards 'alumni charges'. No such charge was mentioned at the time of admission.",
            "My transfer certificate and migration certificate have been pending at {institution} for {days} days. I have submitted the no-dues form and the receipt for all fees, but the administrative officer keeps giving new reasons. I need the documents to join another programme.",
            "Despite repeated written requests, {institution} has not issued the migration certificate to several students of {programme}. The institution is insisting on a clearance from the hostel even for day scholars. This is causing hardship during the admission season.",
        ],
    },
    "RAGGING_DISCRIMINATION": {
        "RAGGING_HOSTEL": [
            "Some junior students at {institution} are being harassed by senior students in the hostel. The affected students are afraid to attend classes and have requested that their names not be disclosed. The situation has continued for several weeks despite informal complaints to the warden.",
            "A group of senior students at {institution} has been intimidating first-year students in the hostel. The complainants are not comfortable giving details in writing because they fear retaliation. We request a discreet inquiry and protective measures.",
            "Students at {institution} have reported being pressured by seniors in the hostel during the {sem} semester. The matter was brought to the notice of the hostel staff, but no action was taken. The students are anxious and want the institution to activate its anti-ragging mechanism.",
        ],
        "DISCRIMINATION_CASTE_GENDER": [
            "Some students at {institution} have faced discriminatory remarks from staff and fellow students on the basis of their background. The comments have created a hostile atmosphere in the {department} department. The affected students are reluctant to complain formally.",
            "A group of students at {institution} has reported differential treatment in the allotment of hostel rooms and internal marks. The pattern suggests discrimination, although the students have not named anyone in this complaint. We request a confidential review.",
            "Students from a particular region at {institution} have been subjected to discriminatory comments by a faculty member. The matter was reported to the Head of Department, but no remedial action was taken. The students are concerned about their academic future.",
        ],
        "HARASSMENT_GENERAL": [
            "Some students at {institution} have reported harassment by senior students and are afraid to attend classes. The complaint is being made in general terms because the students fear that their identity will be revealed. Kindly ensure a discreet inquiry and counseling support.",
            "A few students at {institution} have described being intimidated on campus and have requested confidentiality. They have not named any individual and only want the institution to take preventive action. The anti-ragging committee has not met so far.",
            "The student association at {institution} has received reports of harassment from a group of students. The complainants are unwilling to give written statements at this stage. We request the institution to conduct an awareness session and provide a safe reporting channel.",
        ],
    },
    "GOVERNANCE_MISCONDUCT": {
        "MANAGEMENT_DISPUTE": [
            "There is an ongoing dispute within the management of {institution} that is affecting academic administration. Two groups are claiming control of the institution, and staff members are being asked to follow conflicting instructions. Salary payments and examinations have been disrupted.",
            "A leadership dispute at {institution} has led to the abrupt removal of the Principal and several department heads. The new management has not been recognised by the university. Students and faculty members are uncertain about the validity of decisions taken during this period.",
            "The management of {institution} has been changed without following the prescribed procedure. The new office-bearers are not permitting the academic council to meet. This is affecting approvals and the smooth conduct of the {sem} semester.",
        ],
        "FUND_MISUSE": [
            "Fee collections at {institution} are not being deposited in the official bank account. Parents have been asked to transfer money to a personal account for 'management seats'. No proper receipt is being issued and the accounts are not being audited.",
            "The institution has received funds under a government scheme, but the amount has not been utilised for the intended purpose. The laboratory equipment sanctioned under the scheme is missing, while the utilisation certificate claims full expenditure.",
            "There are reports that funds collected for student welfare at {institution} were diverted to a trust controlled by the management. The student association has requested an audit but has not received the records.",
        ],
        "FAKE_DOCUMENTS": [
            "The documents submitted by {institution} for approval appear to contain discrepancies. The faculty list includes names that do not match the payroll records, and the land documents show an area different from the approved layout. Kindly verify the originals.",
            "A copy of the approval application of {institution} shows signatures that appear to have been obtained without the consent of the faculty members named. The institution may have submitted fabricated experience certificates. An independent verification is required.",
            "The institution has submitted a fake fire safety certificate and an inflated faculty list to obtain approval. Former employees have confirmed that the documents were prepared by the management. Kindly cause an inquiry.",
        ],
    },
    "OTHER": {
        "TRANSPORT": [
            "The bus fee at {institution} was increased by Rs. {amount} without any notice. Students who have not paid the revised amount are being denied transport even though they have paid the academic fee. The bus contractor says the increase is on the instructions of the management.",
            "The college buses at {institution} are overcrowded and do not follow the prescribed routes. Students from {locality} have no pickup point and are forced to arrange private transport. The transport fee is still being collected in full.",
            "The transport facility promised in the prospectus has been discontinued for {programme} students. No refund of the transport fee of Rs. {amount} has been given. Kindly direct the institution to either provide the service or refund the amount.",
        ],
        "SCHOLARSHIP": [
            "The scholarship amount for {year} has not been credited to the bank account of several students at {institution}. The institution collected the bank details and Aadhaar-linked consent but has not forwarded the applications. The students are from low-income families.",
            "Students eligible for a state scholarship at {institution} were asked to pay the full fee pending disbursement. The scholarship has now been credited to the institution's account, but the amount has not been refunded to the students. The accounts section is not giving a clear answer.",
            "The institution has not verified the scholarship applications of {programme} students despite the last date being {date}. Students who submitted complete documents are being marked as ineligible without explanation.",
        ],
        "GENERAL_GRIEVANCE": [
            "I wish to bring to your notice a matter concerning {institution} that has not been addressed by the institution's grievance cell. The issue affects a group of students in {programme}. I have attached the representation submitted to the college and the acknowledgement received.",
            "Despite repeated requests, {institution} has not responded to the representation submitted by the students of {programme}. The matter concerns the facilities promised at the time of admission. Kindly direct the institution to communicate a decision.",
            "The grievance relates to the conduct of {institution} in a matter affecting students of {year}. The institution's reply has been evasive and does not address the specific points raised. I request AICTE to obtain a factual report.",
        ],
    },
}

LEGAL_BOILERPLATE = [
    "The above facts are stated on the basis of records available with the complainant and may be verified from the institution's files.",
    "A copy of the relevant representation and the acknowledgement issued by the institution are enclosed for kind perusal.",
    "The complainant reserves the right to place additional documents on record after receiving the institution's reply.",
    "This representation is made in the public interest and without any intention to prejudice the institution's lawful defence.",
]

TRAILING_LINES = [
    "Kindly do the needful at the earliest.",
    "Thanking you in anticipation.",
    "I shall be grateful for an early inquiry.",
    "Please treat this as urgent.",
    "Awaiting your response.",
]

HINGLISH_LINES = [
    "Sir, hum log bahut pareshan hain, koi sunwai nahi ho rahi.",
    "College walon ne bola management decision hai, hum kuch nahi kar sakte.",
    "Please sir, is matter mein jaldi action lijiye.",
    "Humne kitni baar bola phir bhi koi reply nahi aaya.",
    "Ye paisa hamare ghar ki mehnat ka hai, please help kijiye.",
]

NOISE_CAPS = [
    "PLEASE LOOK INTO THIS MATTER URGENTLY",
    "NO ACTION HAS BEEN TAKEN SO FAR",
    "THIS IS A GENUINE COMPLAINT FROM STUDENTS",
]

MASKED_CONTACTS = [
    "98XXXXXX21",
    "87XXXXXX04",
    "r***@gmail.com",
    "s***@yahoo.com",
    "student.***@example.invalid",
]

INDIC_TEMPLATES = {
    "hi": {
        "FEE": "महोदय, {institution} में {programme} के लिए {year} में निर्धारित शुल्क से अधिक राशि ली गई। रसीद संख्या {receipt} उपलब्ध नहीं कराई गई। कृपया मामले की जांच कर उचित कार्रवाई करें।",
        "FACULTY": "महोदय, {institution} के {department} विभाग में शिक्षकों की भारी कमी है और कक्षाएं नियमित नहीं हो रही हैं। कृपया स्थिति की जांच कराएं।",
        "INFRASTRUCTURE": "महोदय, {institution} की प्रयोगशाला और छात्रावास में आवश्यक सुविधाएं नहीं हैं। छात्रों की सुरक्षा को ध्यान में रखते हुए निरीक्षण कराया जाए।",
        "APPROVAL_VIOLATION": "महोदय, {institution} में स्वीकृत संख्या से अधिक प्रवेश दिए गए हैं। कृपया अनुमोदन की स्थिति की जांच कर कार्रवाई करें।",
        "ACADEMIC_ADMINISTRATION": "महोदय, {institution} में {programme} के परीक्षा परिणाम समय पर घोषित नहीं किए गए। कृपया संस्थान को निर्देश दें।",
        "RAGGING_DISCRIMINATION": "महोदय, {institution} में कुछ छात्रों को परेशान किया जा रहा है और वे कक्षाओं में आने से डर रहे हैं। कृपया गोपनीय जांच कराएं।",
        "GOVERNANCE_MISCONDUCT": "महोदय, {institution} के प्रबंधन और धन के उपयोग में अनियमितता की शिकायत है। कृपया जांच कराएं।",
        "OTHER": "महोदय, {institution} से संबंधित एक शिकायत दर्ज करनी है। कृपया उचित कार्रवाई करें।",
    },
    "ta": {
        "FEE": "ஐயா, {institution} இல் {programme} படிப்பிற்கு நிர்ணயிக்கப்பட்ட கட்டணத்தை விட அதிகம் வசூலிக்கப்பட்டது. ரசீது எண் {receipt} வழங்கப்படவில்லை. தயவுசெய்து விசாரணை செய்யவும்.",
        "FACULTY": "ஐயா, {institution} இன் {department} துறையில் ஆசிரியர் பற்றாக்குறை உள்ளது. வகுப்புகள் தொடர்ந்து நடைபெறவில்லை. தயவுசெய்து ஆய்வு செய்யவும்.",
        "INFRASTRUCTURE": "ஐயா, {institution} இல் ஆய்வகம் மற்றும் விடுதி வசதிகள் போதுமானதாக இல்லை. பாதுகாப்பை கருத்தில் கொண்டு ஆய்வு செய்யவும்.",
        "APPROVAL_VIOLATION": "ஐயா, {institution} இல் அனுமதிக்கப்பட்ட இடங்களுக்கு மேல் மாணவர் சேர்க்கை நடந்துள்ளது. தயவுசெய்து சரிபார்க்கவும்.",
        "ACADEMIC_ADMINISTRATION": "ஐயா, {institution} இல் {programme} தேர்வு முடிவுகள் தாமதமாகின்றன. விரைவில் வெளியிட நடவடிக்கை எடுக்கவும்.",
        "RAGGING_DISCRIMINATION": "ஐயா, {institution} இல் சில மாணவர்கள் தொந்தரவு செய்யப்படுகிறார்கள். ரகசிய விசாரணை நடத்தவும்.",
        "GOVERNANCE_MISCONDUCT": "ஐயா, {institution} நிர்வாகத்தில் நிதி முறைகேடு குறித்து புகார் உள்ளது. விசாரணை நடத்தவும்.",
        "OTHER": "ஐயா, {institution} தொடர்பான புகாரை பதிவு செய்கிறேன். தயவுசெய்து நடவடிக்கை எடுக்கவும்.",
    },
    "te": {
        "FEE": "గౌరవనీయులారా, {institution} లో {programme} కోసం నిర్ణయించిన ఫీజు కంటే ఎక్కువ వసూలు చేశారు. రసీదు నంబర్ {receipt} ఇవ్వలేదు. దయచేసి విచారణ చేయండి.",
        "FACULTY": "గౌరవనీయులారా, {institution} లోని {department} విభాగంలో అధ్యాపకుల కొరత ఉంది. తరగతులు సక్రమంగా జరగడం లేదు. దయచేసి పరిశీలించండి.",
        "INFRASTRUCTURE": "గౌరవనీయులారా, {institution} లో ప్రయోగశాల మరియు వసతి గృహ సౌకర్యాలు సరిపోవు. దయచేసి తనిఖీ చేయండి.",
        "APPROVAL_VIOLATION": "గౌరవనీయులారా, {institution} లో అనుమతించిన సీట్ల కంటే ఎక్కువ ప్రవేశాలు ఇచ్చారు. దయచేసి పరిశీలించండి.",
        "ACADEMIC_ADMINISTRATION": "గౌరవనీయులారా, {institution} లో {programme} పరీక్ష ఫలితాలు ఆలస్యమవుతున్నాయి. వెంటనే విడుదల చేయించండి.",
        "RAGGING_DISCRIMINATION": "గౌరవనీయులారా, {institution} లో కొందరు విద్యార్థులను ఇబ్బంది పెడుతున్నారు. గోప్యంగా విచారణ చేయండి.",
        "GOVERNANCE_MISCONDUCT": "గౌరవనీయులారా, {institution} నిర్వహణలో నిధుల దుర్వినియోగం జరిగిందని ఆరోపణ ఉంది. విచారణ చేయండి.",
        "OTHER": "గౌరవనీయులారా, {institution} కు సంబంధించిన ఫిర్యాదును నమోదు చేస్తున్నాను. దయచేసి చర్య తీసుకోండి.",
    },
    "bn": {
        "FEE": "মহোদয়, {institution} এ {programme} কোর্সের জন্য নির্ধারিত ফি-এর চেয়ে বেশি টাকা নেওয়া হয়েছে। রসিদ নম্বর {receipt} দেওয়া হয়নি। অনুগ্রহ করে তদন্ত করুন।",
        "FACULTY": "মহোদয়, {institution} এর {department} বিভাগে শিক্ষকের ঘাটতি রয়েছে। ক্লাস নিয়মিত হচ্ছে না। অনুগ্রহ করে পরিদর্শন করুন।",
        "INFRASTRUCTURE": "মহোদয়, {institution} এর ল্যাবরেটরি ও হোস্টেলের সুবিধা যথেষ্ট নয়। নিরাপত্তার কথা ভেবে তদন্ত করুন।",
        "APPROVAL_VIOLATION": "মহোদয়, {institution} এ অনুমোদিত আসনের বেশি ভর্তি করা হয়েছে। অনুগ্রহ করে যাচাই করুন।",
        "ACADEMIC_ADMINISTRATION": "মহোদয়, {institution} এ {programme} পরীক্ষার ফলাফল দেরিতে প্রকাশ হচ্ছে। দ্রুত ব্যবস্থা নিন।",
        "RAGGING_DISCRIMINATION": "মহোদয়, {institution} এ কিছু শিক্ষার্থীকে হয়রানি করা হচ্ছে। গোপন তদন্তের ব্যবস্থা করুন।",
        "GOVERNANCE_MISCONDUCT": "মহোদয়, {institution} এর পরিচালনায় অর্থের অনিয়মের অভিযোগ রয়েছে। তদন্ত করুন।",
        "OTHER": "মহোদয়, {institution} সম্পর্কিত একটি অভিযোগ জানাচ্ছি। অনুগ্রহ করে ব্যবস্থা নিন।",
    },
    "mr": {
        "FEE": "महोदय, {institution} मध्ये {programme} साठी निर्धारित शुल्कापेक्षा जास्त रक्कम घेतली गेली. पावती क्रमांक {receipt} दिली नाही. कृपया चौकशी करून कारवाई करा.",
        "FACULTY": "महोदय, {institution} च्या {department} विभागात शिक्षकांची कमतरता आहे. वर्ग नियमित होत नाहीत. कृपया पाहणी करा.",
        "INFRASTRUCTURE": "महोदय, {institution} मधील प्रयोगशाळा आणि वसतिगृहाच्या सुविधा अपुर्या आहेत. कृपया तपासणी करा.",
        "APPROVAL_VIOLATION": "महोदय, {institution} मध्ये मंजूर प्रवेशक्षमतेपेक्षा जास्त प्रवेश घेतले आहेत. कृपया तपासणी करा.",
        "ACADEMIC_ADMINISTRATION": "महोदय, {institution} मध्ये {programme} चे परीक्षा निकाल उशिरा जाहीर होत आहेत. त्वरित कारवाई करा.",
        "RAGGING_DISCRIMINATION": "महोदय, {institution} मध्ये काही विद्यार्थ्यांना त्रास दिला जात आहे. गोपनीय चौकशी करा.",
        "GOVERNANCE_MISCONDUCT": "महोदय, {institution} च्या व्यवस्थापनात निधीचा गैरवापर झाल्याची तक्रार आहे. चौकशी करा.",
        "OTHER": "महोदय, {institution} संबंधित तक्रार नोंदवत आहे. कृपया योग्य कारवाई करा.",
    },
}

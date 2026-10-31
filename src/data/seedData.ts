import {
  User,
  Electrician,
  ServiceRequest,
  Job,
  JobTimelineEvent,
  ApprovalRequest,
  EscalationAlert,
  AuditLogEntry,
  NotificationItem,
  PolicySettings,
  LocationCoordinates,
  ProblemCategory,
  JobPriority,
  JobStatus,
  DisruptionRecord,
} from '../types';

// Base Metro Center: Mysuru, Karnataka, India (near KR Circle & Mysore Palace)
export const METRO_CENTER = { lat: 12.2958, lng: 76.6394 };

// Geographically authentic Mysuru localities and realistic coordinates
export const MYSURU_LOCALITIES = [
  { name: 'Saraswathipuram', lat: 12.3025, lng: 76.6315, postalCode: '570009', areaDesc: 'Residential & Institutional Zone' },
  { name: 'Kuvempunagar', lat: 12.2855, lng: 76.6268, postalCode: '570023', areaDesc: 'South Mysuru Residential Sector' },
  { name: 'Vijayanagar 2nd Stage', lat: 12.3360, lng: 76.6060, postalCode: '570017', areaDesc: 'North-West Residential Enclave' },
  { name: 'Jayalakshmipuram', lat: 12.3210, lng: 76.6265, postalCode: '570012', areaDesc: 'Central Residential & Commercial' },
  { name: 'Hebbal Industrial Area', lat: 12.3650, lng: 76.5980, postalCode: '570016', areaDesc: 'Heavy Manufacturing & IT Hub' },
  { name: 'Bogadi 2nd Stage', lat: 12.2980, lng: 76.5985, postalCode: '570026', areaDesc: 'West Mysuru Residential Area' },
  { name: 'Hootagalli Industrial Area', lat: 12.3480, lng: 76.5750, postalCode: '570018', areaDesc: 'Industrial Substation Corridor' },
  { name: 'Nazarbad', lat: 12.3090, lng: 76.6660, postalCode: '570010', areaDesc: 'Heritage East Zone & Government Offices' },
  { name: 'Bannimantap', lat: 12.3340, lng: 76.6490, postalCode: '570015', areaDesc: 'Commercial & Transport Corridor' },
  { name: 'Siddhartha Layout', lat: 12.2990, lng: 76.6840, postalCode: '570011', areaDesc: 'East Mysuru Residential Sector' },
  { name: 'Gokulam 3rd Stage', lat: 12.3315, lng: 76.6270, postalCode: '570002', areaDesc: 'Cultural & Residential District' },
  { name: 'Yadavagiri', lat: 12.3240, lng: 76.6410, postalCode: '570020', areaDesc: 'Railway & Industrial Edge' },
  { name: 'Chamundipuram', lat: 12.2905, lng: 76.6540, postalCode: '570004', areaDesc: 'South-East Commercial Hub' },
  { name: 'Metagalli', lat: 12.3520, lng: 76.6280, postalCode: '570016', areaDesc: 'North Industrial Area' },
  { name: 'Vidyaranyapuram', lat: 12.2780, lng: 76.6490, postalCode: '570008', areaDesc: 'Industrial & Residential Belt' },
  { name: 'TK Layout', lat: 12.3060, lng: 76.6150, postalCode: '570009', areaDesc: 'West University Quarter' },
  { name: 'Sayyaji Rao Road', lat: 12.3120, lng: 76.6510, postalCode: '570001', areaDesc: 'Central CBD & Retail District' },
  { name: 'Alanahalli', lat: 12.2910, lng: 76.7020, postalCode: '570028', areaDesc: 'Ring Road Peripheral Junction' },
  { name: 'Devaraja Mohalla', lat: 12.3085, lng: 76.6480, postalCode: '570001', areaDesc: 'Commercial Core & Historic Market' },
  { name: 'KRS Road Industrial Hub', lat: 12.3580, lng: 76.6120, postalCode: '570016', areaDesc: 'North-West Feeder Corridor' },
];

export function getMysuruLocality(index: number) {
  return MYSURU_LOCALITIES[index % MYSURU_LOCALITIES.length];
}

// Jitter helper within actual Mysuru service radius (2 - 8 km)
export function getOffsetLocation(index: number): { lat: number; lng: number } {
  const loc = getMysuruLocality(index);
  // deterministic subtle scatter within neighborhood (~200m)
  const angle = (index * 137.5 * Math.PI) / 180;
  const radius = 0.002 + ((index % 5) * 0.0015);
  return {
    lat: Number((loc.lat + radius * Math.cos(angle)).toFixed(6)),
    lng: Number((loc.lng + radius * Math.sin(angle)).toFixed(6)),
  };
}

export const SEED_POLICIES: PolicySettings = {
  autoDispatchEnabled: true,
  autoDispatchMinScoreThreshold: 75,
  emergencyAutoEscalate: true,
  maxDailyWorkloadHours: 8.5,
  slaHighPriorityMinutes: 120,
  slaEmergencyMinutes: 45,
  requireManagementApprovalForReassignmentsCount: 3,
  weights: {
    skillCompatibility: 25,
    availabilityShift: 20,
    proximityTravel: 20,
    workloadBalance: 15,
    deadlineFeasibility: 10,
    equipmentMatch: 10,
  },
};

// 1. SYSTEM USERS & STAKEHOLDERS (Localized to Mysuru, Karnataka)
export const SEED_USERS: User[] = [
  // Supervisor (Monitoring Only role per specification)
  {
    id: 'usr-sup-1',
    name: 'Meera Kulkarni',
    email: 'supervisor@dispatchgrid.io',
    role: 'supervisor',
    phone: '+91 821 2419100',
    avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150',
    department: 'Mysuru Grid Operations Centre',
    active: true,
    createdAt: '2025-01-15T08:00:00Z',
  },
  // Backward compatible alias for operations
  {
    id: 'usr-ops-1',
    name: 'Meera Kulkarni',
    email: 'operations@dispatchgrid.io',
    role: 'supervisor',
    phone: '+91 821 2419100',
    avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150',
    department: 'Mysuru Operations Control',
    active: true,
    createdAt: '2025-01-15T08:00:00Z',
  },
  // Primary Demo Customer (Individual) - Ananya Rao
  {
    id: 'usr-cust-ind-1',
    name: 'Ananya Rao',
    email: 'customer@dispatchgrid.io',
    role: 'customer',
    phone: '+91 98450 21001',
    customerCategory: 'individual',
    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150',
    active: true,
    createdAt: '2025-03-01T08:00:00Z',
  },
  // Primary Demo Customer (Commercial) - Mysore Silk & Handicrafts Emporium
  {
    id: 'usr-cust-com-1',
    name: 'Suresh Nambiar',
    email: 'facilities@mysoresilk.in',
    role: 'customer',
    phone: '+91 821 2419001',
    customerCategory: 'commercial',
    companyName: 'Mysore Silk & Handicrafts Emporium',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150',
    active: true,
    createdAt: '2025-03-02T08:00:00Z',
    commercialLocations: [
      {
        lat: 12.3120,
        lng: 76.6510,
        address: '#45, Sayyaji Rao Road, Near K.R. Circle',
        city: 'Mysuru',
        postalCode: '570001',
      },
      {
        lat: 12.3650,
        lng: 76.5980,
        address: 'Plot 12-B, Hebbal Industrial Area, Phase 1',
        city: 'Mysuru',
        postalCode: '570016',
      },
      {
        lat: 12.2905,
        lng: 76.6540,
        address: '#89, Chamundi Hill Main Road, Chamundipuram',
        city: 'Mysuru',
        postalCode: '570004',
      },
    ],
  },
];

// Additional 29 Individual Customers across Mysuru neighborhoods
const INDIVIDUAL_NAMES = [
  'Rohan Shetty', 'Kavya Gowda', 'Arjun Kumar', 'Sunita Patil', 'Ramesh Hebbar',
  'Pooja Hegde', 'Naveen Someshwar', 'Deepa Nayak', 'Vikram Desai', 'Shweta Acharya',
  'Kiran Kulkarni', 'Archana Bhat', 'Manohar Shetty', 'Divya Prasad', 'Vinay Kumar',
  'Rashmi Rao', 'Raghavendra Joshi', 'Swathi Deshpande', 'Girish Gowda', 'Sindhu Urs',
  'Chetan Murthy', 'Sahana Hegde', 'Prashanth Kamath', 'Megha Shastry', 'Guruprasad Bhat',
  'Bhavana Naik', 'Shashi Kiran', 'Varsha Shenoy', 'Dhananjaya Rao'
];

for (let i = 0; i < INDIVIDUAL_NAMES.length; i++) {
  const loc = getMysuruLocality(i + 1);
  SEED_USERS.push({
    id: `usr-cust-ind-${i + 2}`,
    name: INDIVIDUAL_NAMES[i],
    email: `${INDIVIDUAL_NAMES[i].toLowerCase().replace(/\s+/g, '.')}@example.in`,
    role: 'customer',
    customerCategory: 'individual',
    phone: `+91 98450 ${(22000 + i).toString()}`,
    avatar: `https://images.unsplash.com/photo-${1534528741775 + i * 555}?w=150`,
    active: true,
    createdAt: '2025-03-10T10:00:00Z',
  });
}

// 9 Additional Commercial Customers in Mysuru
const COMMERCIAL_COMPANIES = [
  { name: 'Hebbal Software Tech Park', contact: 'Karthik Somayaji', locIdx: 4 },
  { name: 'Chamundi Cold Storage Facilities', contact: 'Mohan Ram', locIdx: 6 },
  { name: 'Cauvery Healthcare Hospital', contact: 'Dr. Savitha Hegde', locIdx: 1 },
  { name: 'Hootagalli Auto Component Plant', contact: 'Raghavan Iyer', locIdx: 6 },
  { name: 'Devaraja Market Agro Logistics', contact: 'Basavaraj Patil', locIdx: 18 },
  { name: 'Gokulam Heritage Boutique Suites', contact: 'Nandini Urs', locIdx: 10 },
  { name: 'Metagalli Precision Tools Ltd', contact: 'Sridhar Nayak', locIdx: 13 },
  { name: 'Bannimantap Commercial Transporters', contact: 'Syed Tanveer', locIdx: 8 },
  { name: 'Siddhartha Educational Trust', contact: 'Prof. Ananth Murthy', locIdx: 9 },
];

for (let i = 0; i < COMMERCIAL_COMPANIES.length; i++) {
  const loc = getMysuruLocality(COMMERCIAL_COMPANIES[i].locIdx);
  SEED_USERS.push({
    id: `usr-cust-com-${i + 2}`,
    name: COMMERCIAL_COMPANIES[i].contact,
    companyName: COMMERCIAL_COMPANIES[i].name,
    email: `facilities@${COMMERCIAL_COMPANIES[i].name.toLowerCase().replace(/[^a-z]/g, '')}.in`,
    role: 'customer',
    customerCategory: 'commercial',
    phone: `+91 821 ${(2419010 + i).toString()}`,
    active: true,
    createdAt: '2025-03-12T11:00:00Z',
    commercialLocations: [
      {
        lat: loc.lat,
        lng: loc.lng,
        address: `#${100 + i * 15}, Industrial Sector, ${loc.name}`,
        city: 'Mysuru',
        postalCode: loc.postalCode,
      },
    ],
  });
}

// 2. FIELD TECHNICIANS (20 Certified Electricians in Mysuru, Karnataka)
export const SKILLS_POOL = [
  'High Voltage Systems',
  'Commercial Lighting',
  'Industrial Wiring',
  'Panel & Breaker Upgrades',
  'Solar & Inverter Systems',
  'EV Charging Stations',
  'Emergency Generators',
  'Cable Fault Diagnostics',
  'Arc Flash Mitigation',
  'Switchgear Maintenance',
  'Residential Wiring',
  'HVAC Power Integration',
  'Thermal Imaging Inspection',
  'Substation Maintenance',
];

export const EQUIPMENT_POOL = [
  'Thermal Imaging Camera',
  'High-Voltage Arc Flash PPE (Cat 4)',
  'Digital Cable Fault Locator',
  'Insulated Tool Set (1000V)',
  'Megohmmeter / Insulation Tester',
  '3-Phase Power Quality Analyzer',
  'Hydraulic Conduit Bender',
  'Industrial Generator Diagnostic Kit',
  'Solar Array Testing Meter',
  'Utility Bucket Van',
];

const TECH_DATA = [
  {
    name: 'Pradeep Hegde',
    email: 'technician@dispatchgrid.io',
    skills: ['High Voltage Systems', 'Panel & Breaker Upgrades', 'Emergency Generators', 'Switchgear Maintenance', 'Arc Flash Mitigation'],
    certs: ['CHESCOM Certified Master Electrician', 'Grade 1 Wireman License (Karnataka)', 'NFPA 70E Certified'],
    equipment: ['High-Voltage Arc Flash PPE (Cat 4)', 'Megohmmeter / Insulation Tester', 'Insulated Tool Set (1000V)'],
    shift: 'morning' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 3.5,
    locIdx: 0, // Saraswathipuram
  },
  {
    name: 'Sandeep Gowda',
    email: 'sandeep.g@dispatchgrid.io',
    skills: ['Commercial Lighting', 'Industrial Wiring', 'Cable Fault Diagnostics', 'Thermal Imaging Inspection'],
    certs: ['Karnataka Electrical Inspectorate Class 1', 'Infrared Thermography L1'],
    equipment: ['Thermal Imaging Camera', 'Digital Cable Fault Locator', 'Insulated Tool Set (1000V)'],
    shift: 'morning' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 6.0,
    locIdx: 1, // Kuvempunagar
  },
  {
    name: 'Manjunath Bhat',
    email: 'manjunath.b@dispatchgrid.io',
    skills: ['Solar & Inverter Systems', 'EV Charging Stations', 'Residential Wiring'],
    certs: ['MNRE Certified Solar PV Technician', 'EV Supply Equipment Specialist'],
    equipment: ['Solar Array Testing Meter', 'Insulated Tool Set (1000V)'],
    shift: 'flexible' as const,
    shiftHours: { start: '08:30', end: '17:00' },
    workload: 2.0,
    locIdx: 2, // Vijayanagar
  },
  {
    name: 'Kiran Shetty',
    email: 'kiran.s@dispatchgrid.io',
    skills: ['High Voltage Systems', 'Switchgear Maintenance', 'Arc Flash Mitigation'],
    certs: ['Master Wireman KPTCL', 'Medium Voltage Safety Cert'],
    equipment: ['High-Voltage Arc Flash PPE (Cat 4)', '3-Phase Power Quality Analyzer'],
    shift: 'afternoon' as const,
    shiftHours: { start: '12:00', end: '20:30' },
    workload: 4.5,
    locIdx: 4, // Hebbal
  },
  {
    name: 'Naveen Rao',
    email: 'naveen.r@dispatchgrid.io',
    skills: ['Emergency Generators', 'HVAC Power Integration', 'Panel & Breaker Upgrades'],
    certs: ['Diesel Genset Master Tech', 'Certified Industrial Electrician'],
    equipment: ['Industrial Generator Diagnostic Kit', 'Insulated Tool Set (1000V)'],
    shift: 'morning' as const,
    shiftHours: { start: '07:30', end: '16:00' },
    workload: 5.0,
    locIdx: 6, // Hootagalli
  },
  {
    name: 'Venkatesh Prasad',
    email: 'venkatesh.p@dispatchgrid.io',
    skills: ['Cable Fault Diagnostics', 'Thermal Imaging Inspection', 'Industrial Wiring'],
    certs: ['Fluke Certified High-Accuracy Diagnostics', 'Grade 1 License'],
    equipment: ['Thermal Imaging Camera', 'Digital Cable Fault Locator'],
    shift: 'morning' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 1.5,
    locIdx: 3, // Jayalakshmipuram
  },
  {
    name: 'Mahesh Shastry',
    email: 'mahesh.s@dispatchgrid.io',
    skills: ['Residential Wiring', 'Panel & Breaker Upgrades', 'Commercial Lighting'],
    certs: ['Residential Wireman Licence', 'Safety Compliance Specialist'],
    equipment: ['Insulated Tool Set (1000V)', 'Megohmmeter / Insulation Tester'],
    shift: 'flexible' as const,
    shiftHours: { start: '09:00', end: '17:30' },
    workload: 3.0,
    locIdx: 5, // Bogadi
  },
  {
    name: 'Raghu Nayak',
    email: 'raghu.n@dispatchgrid.io',
    skills: ['High Voltage Systems', 'Cable Fault Diagnostics', 'Arc Flash Mitigation'],
    certs: ['KPTCL Substation Maintenance Specialist', 'Master Electrician'],
    equipment: ['High-Voltage Arc Flash PPE (Cat 4)', 'Digital Cable Fault Locator'],
    shift: 'night' as const,
    shiftHours: { start: '20:00', end: '04:30' },
    workload: 0.0,
    locIdx: 7, // Nazarbad
  },
  {
    name: 'Chidan Kumar',
    email: 'chidan.k@dispatchgrid.io',
    skills: ['Residential Wiring', 'Panel & Breaker Upgrades', 'Commercial Lighting'],
    certs: ['Certified Domestic Wireman', 'Energy Auditor Assistant'],
    equipment: ['Insulated Tool Set (1000V)'],
    shift: 'morning' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 4.0,
    locIdx: 8, // Bannimantap
  },
  {
    name: 'Deepak Murthy',
    email: 'deepak.m@dispatchgrid.io',
    skills: ['Industrial Wiring', 'Switchgear Maintenance', '3-Phase Power Quality Analyzer'],
    certs: ['Industrial Plant Electrician', 'CEA Safety Regulations Cert'],
    equipment: ['3-Phase Power Quality Analyzer', 'Megohmmeter / Insulation Tester'],
    shift: 'morning' as const,
    shiftHours: { start: '07:30', end: '16:00' },
    workload: 6.5,
    locIdx: 9, // Siddhartha Layout
  },
  {
    name: 'Prakash Acharya',
    email: 'prakash.a@dispatchgrid.io',
    skills: ['Commercial Lighting', 'Residential Wiring', 'Panel & Breaker Upgrades'],
    certs: ['Licensed Journeyman Wireman'],
    equipment: ['Insulated Tool Set (1000V)'],
    shift: 'afternoon' as const,
    shiftHours: { start: '13:00', end: '21:30' },
    workload: 2.5,
    locIdx: 10, // Gokulam
  },
  {
    name: 'Girish Deshpande',
    email: 'girish.d@dispatchgrid.io',
    skills: ['Emergency Generators', 'High Voltage Systems', 'Switchgear Maintenance'],
    certs: ['Master Industrial Electrician', 'Substation Operator'],
    equipment: ['Industrial Generator Diagnostic Kit', 'High-Voltage Arc Flash PPE (Cat 4)'],
    shift: 'morning' as const,
    shiftHours: { start: '07:00', end: '15:30' },
    workload: 5.5,
    locIdx: 11, // Yadavagiri
  },
  {
    name: 'Harish Poojary',
    email: 'harish.p@dispatchgrid.io',
    skills: ['Solar & Inverter Systems', 'EV Charging Stations', 'Thermal Imaging Inspection'],
    certs: ['NABCEP Equivalent Solar PV Pro', 'Level 2 Thermography'],
    equipment: ['Thermal Imaging Camera', 'Solar Array Testing Meter'],
    shift: 'morning' as const,
    shiftHours: { start: '08:30', end: '17:00' },
    workload: 1.0,
    locIdx: 12, // Chamundipuram
  },
  {
    name: 'Santosh Nayak',
    email: 'santosh.n@dispatchgrid.io',
    skills: ['Cable Fault Diagnostics', 'Industrial Wiring', 'Panel & Breaker Upgrades'],
    certs: ['Journeyman Wireman (Karnataka)'],
    equipment: ['Digital Cable Fault Locator', 'Insulated Tool Set (1000V)'],
    shift: 'flexible' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 3.5,
    locIdx: 13, // Metagalli
  },
  {
    name: 'Vinay Shenoy',
    email: 'vinay.s@dispatchgrid.io',
    skills: ['HVAC Power Integration', 'Commercial Lighting', 'Panel & Breaker Upgrades'],
    certs: ['Certified Wireman', 'Industrial HVAC Controls Specialist'],
    equipment: ['Insulated Tool Set (1000V)', 'Megohmmeter / Insulation Tester'],
    shift: 'morning' as const,
    shiftHours: { start: '07:30', end: '16:00' },
    workload: 5.5,
    locIdx: 14, // Vidyaranyapuram
  },
  {
    name: 'Ashok Varadarajan',
    email: 'ashok.v@dispatchgrid.io',
    skills: ['High Voltage Systems', 'Switchgear Maintenance', 'Thermal Imaging Inspection'],
    certs: ['Master Electrician', 'High-Tension Line Cert'],
    equipment: ['High-Voltage Arc Flash PPE (Cat 4)', 'Thermal Imaging Camera'],
    shift: 'afternoon' as const,
    shiftHours: { start: '11:00', end: '19:30' },
    workload: 4.0,
    locIdx: 15, // TK Layout
  },
  {
    name: 'Mohan Das',
    email: 'mohan.d@dispatchgrid.io',
    skills: ['Residential Wiring', 'EV Charging Stations', 'Smart Energy Metering'],
    certs: ['Residential Wireman Licence'],
    equipment: ['Insulated Tool Set (1000V)'],
    shift: 'morning' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 2.0,
    locIdx: 16, // Sayyaji Rao Road
  },
  {
    name: 'Guruprasad Rao',
    email: 'guruprasad.r@dispatchgrid.io',
    skills: ['Emergency Generators', 'Industrial Wiring', 'Arc Flash Mitigation'],
    certs: ['Industrial Master Wireman', 'Safety Council Cert'],
    equipment: ['Industrial Generator Diagnostic Kit', 'High-Voltage Arc Flash PPE (Cat 4)'],
    shift: 'flexible' as const,
    shiftHours: { start: '07:00', end: '15:30' },
    workload: 4.0,
    locIdx: 17, // Alanahalli
  },
  {
    name: 'Sridhar Joshi',
    email: 'sridhar.j@dispatchgrid.io',
    skills: ['Commercial Lighting', 'Cable Fault Diagnostics', 'Thermal Imaging Inspection'],
    certs: ['Grade 1 Wireman', 'Infrared Thermographer'],
    equipment: ['Thermal Imaging Camera', 'Digital Cable Fault Locator'],
    shift: 'morning' as const,
    shiftHours: { start: '08:00', end: '16:30' },
    workload: 0.0,
    locIdx: 18, // Devaraja Mohalla
  },
  {
    name: 'Anand Kulkarni',
    email: 'anand.k@dispatchgrid.io',
    skills: ['High Voltage Systems', 'Solar & Inverter Systems', 'Switchgear Maintenance'],
    certs: ['Master Electrician', 'Rooftop Solar Specialist'],
    equipment: ['High-Voltage Arc Flash PPE (Cat 4)', 'Solar Array Testing Meter'],
    shift: 'morning' as const,
    shiftHours: { start: '07:30', end: '16:00' },
    workload: 3.0,
    locIdx: 19, // KRS Road Industrial Hub
  },
];

export const SEED_ELECTRICIANS: Electrician[] = TECH_DATA.map((t, idx) => {
  const loc = MYSURU_LOCALITIES[t.locIdx % MYSURU_LOCALITIES.length];
  const userId = `usr-tech-${idx + 1}`;
  
  SEED_USERS.push({
    id: userId,
    name: t.name,
    email: t.email,
    role: 'technician',
    phone: `+91 98450 ${(31001 + idx).toString()}`,
    avatar: `https://images.unsplash.com/photo-${1535713875002 + idx * 777}?w=150`,
    department: 'Mysuru Electrical Field Operations',
    employeeId: `MYS-TECH-${100 + idx}`,
    active: true,
    createdAt: '2025-01-20T08:00:00Z',
  });

  const statuses: ('available' | 'busy' | 'en_route')[] = ['available', 'busy', 'en_route'];
  const status = idx === 0 ? 'available' : statuses[idx % 3];

  return {
    id: `elec-${idx + 1}`,
    userId,
    name: t.name,
    employeeId: `MYS-TECH-${100 + idx}`,
    phone: `+91 98450 ${(31001 + idx).toString()}`,
    email: t.email,
    avatar: `https://images.unsplash.com/photo-${1535713875002 + idx * 777}?w=150`,
    skills: t.skills,
    certifications: t.certs,
    equipment: t.equipment,
    shift: t.shift,
    shiftHours: t.shiftHours,
    isAvailable: status !== 'busy',
    status: status,
    currentJobId: status === 'busy' ? `JOB-2026-${4000 + idx}` : null,
    currentWorkload: t.workload,
    maxDailyHours: 8.5,
    currentLocation: {
      lat: loc.lat,
      lng: loc.lng,
      lastUpdated: new Date(Date.now() - (idx * 4 + 2) * 60000).toISOString(),
      isSimulated: true,
    },
    rating: Number((4.6 + (idx % 4) * 0.1).toFixed(1)),
    jobsCompletedTotal: 45 + idx * 12,
  };
});

// 3. GENERATE 100 SERVICE REQUESTS AND JOBS (Distributed across Mysuru)
export const SEED_SERVICE_REQUESTS: ServiceRequest[] = [];
export const SEED_JOBS: Job[] = [];

const PROBLEM_TITLES: Record<ProblemCategory, string[]> = {
  power_outage: [
    'Sudden total building outage during operating hours',
    'Main CHESCOM feeder line power loss affecting western wing',
    'Intermittent power dropouts in critical server room',
    'Distribution transformer phase fuse tripped after rain',
  ],
  wiring_fault: [
    'Burning insulation smell detected near distribution board',
    'Underground conduit insulation exposed in basement',
    'Secondary circuit breaker trips immediately upon reset',
    'Flickering circuits and buzzing junction boxes in workshop',
  ],
  equipment_failure: [
    'Backup emergency diesel generator fails to start during test',
    'Central HVAC compressor starter electrical failure',
    'Freight elevator auxiliary power control board malfunctioning',
    '3-phase induction motor drive tripped with overload code E-402',
  ],
  short_circuit: [
    'Direct ground fault arc flash in distribution sub-panel B',
    'Underground cable trench flooded causing dead short',
    'Exterior perimeter lighting short circuit after monsoon rain',
    'Main kitchen appliance line ground fault trip',
  ],
  lighting_problem: [
    'High-bay warehouse LED fixtures intermittently shutting off',
    'Emergency exit signs and egress illumination dark',
    'Security floodlights photocell sensor failure',
    'Commercial showroom dimming control system unresponsive',
  ],
  panel_breaker: [
    'Main 400A circuit breaker runs excessively hot (82°C)',
    'Subpanel breaker busbar showing oxidation and buzzing',
    'Upgrading residential service from single phase to 3-phase',
    'Tripped 3-phase molded case breaker won’t latch closed',
  ],
  preventive_maintenance: [
    'Quarterly infrared thermographic scan of switchboards',
    'Annual transformer insulation resistance & oil dielectric test',
    'Rooftop solar inverter array scheduled health audit',
    'Bi-annual diesel generator automated transfer switch testing',
  ],
  other: [
    'Dual-port EV fast charger display error code 0x88',
    'Commercial smart metering telemetry disconnection',
    'Substation earthing pit impedance re-testing',
    'Surge protective device module flagged for replacement',
  ],
  residential_wiring: [
    'Residential copper wiring arcing in concealed conduit',
    'Main junction box neutral line burn out in Saraswathipuram villa',
    'Whole-house re-wiring inspection for older residential building',
    'Sub-distribution board insulation degradation',
  ],
  switch_socket: [
    '16A geyser wall socket burnt and charred',
    'AC modular switch sparking upon switching on',
    'Earthing pin voltage leakage detected at kitchen counter sockets',
    'Replacement of worn 6-module switchboard faceplate',
  ],
  lighting_fixture: [
    'Street-facing security halogen high-mast lamp failure',
    'Indoor recessed false-ceiling LED panel driver blown',
    'Chandelier light fixture wiring spark in main hall',
    'Industrial grade fluorescent battens continuous hum and flicker',
  ],
  fan_motor_repair: [
    'Heavy ceiling fan motor winding overheating and seized',
    'Industrial exhaust fan regulator and capacitor burnout',
    'Ceiling fan wobbling with violent electrical humming',
    'Ventilation blower motor trip on thermal overload',
  ],
  three_phase_power: [
    '3-phase submersible pump motor starter contactor stuck',
    'Phase unbalance detected causing 3-phase machinery shutdown',
    'Motor control center relay trip with phase reversal error',
    'Heavy industrial lathe 3-phase main circuit breaker trip',
  ],
  solar_inverter: [
    '5kW rooftop solar grid-tie inverter error code E031',
    'Solar DC isolator switch showing thermal discolouration',
    'Solar panel array string open circuit and generation loss',
    'Micro-inverter communication module offline',
  ],
  ev_charging: [
    'Type-2 AC 7.4kW EV wallbox charger pilot pin fault',
    'Commercial 22kW fast charger earth leakage trip',
    'EV charger emergency stop switch triggered and locked',
    'EV charging cable connector temperature sensor warning',
  ],
  generator_backup: [
    'Automatic Transfer Switch (ATS) fails to switch to DG power',
    'Emergency diesel generator excitation system failure',
    'DG battery charger circuit breaker tripped',
    'Auxiliary alternator voltage fluctuation above safe threshold',
  ],
  transformer_substation: [
    '11kV step-down distribution transformer Buchholz alarm',
    'Transformer neutral grounding resistor earthing check',
    'Oil level indicator drop and temperature alarm at feeder station',
    'HT gang-operated switch insulator cracked',
  ],
  other_electrical: [
    'Lightning arrestor surge counter incremented after storm',
    'UPS battery bank inter-cell connection resistance high',
    'Power factor correction capacitor bank step failure',
    'Electrical earthing pit Megger earth resistance audit',
  ],
};

const CATEGORIES_LIST: ProblemCategory[] = [
  'power_outage',
  'wiring_fault',
  'equipment_failure',
  'short_circuit',
  'lighting_problem',
  'panel_breaker',
  'preventive_maintenance',
  'other',
];

for (let i = 1; i <= 100; i++) {
  const reqId = `REQ-2026-${(1000 + i).toString()}`;
  const jobId = `JOB-2026-${(4000 + i).toString()}`;
  const category = CATEGORIES_LIST[i % CATEGORIES_LIST.length];
  const priority = i % 12 === 0 ? 'emergency' : i % 5 === 0 ? 'high' : i % 3 === 0 ? 'medium' : 'low';

  const isCommercial = i % 4 === 0;
  const custIndex = isCommercial ? (i % 10) + 1 : (i % 30) + 1;
  const custUser = isCommercial 
    ? SEED_USERS.find(u => u.id === `usr-cust-com-${custIndex}`)!
    : SEED_USERS.find(u => u.id === `usr-cust-ind-${custIndex}`)!;

  const titles = PROBLEM_TITLES[category];
  const title = titles[i % titles.length];
  const locality = getMysuruLocality(i);

  const location: LocationCoordinates = {
    lat: locality.lat,
    lng: locality.lng,
    address: isCommercial
      ? `${custUser.companyName || 'Commercial Facility'}, ${locality.name}`
      : `#${24 + i * 2}, ${i % 7 + 1}th Cross, ${locality.name}`,
    city: 'Mysuru',
    postalCode: locality.postalCode,
  };

  let status: JobStatus;
  let assignedElec: Electrician | null = null;
  const estHours = 1.5 + (i % 5) * 0.5;

  if (i <= 5) {
    status = 'submitted';
  } else if (i <= 10) {
    status = 'under_review';
  } else if (i <= 18) {
    status = 'validated';
  } else if (i <= 25) {
    status = 'scheduling';
  } else if (i <= 45) {
    status = 'assigned';
    assignedElec = SEED_ELECTRICIANS[i % SEED_ELECTRICIANS.length];
  } else if (i <= 55) {
    status = 'dispatched';
    assignedElec = SEED_ELECTRICIANS[(i + 2) % SEED_ELECTRICIANS.length];
  } else if (i <= 65) {
    status = 'acknowledged';
    assignedElec = SEED_ELECTRICIANS[(i + 4) % SEED_ELECTRICIANS.length];
  } else if (i <= 72) {
    status = 'en_route';
    assignedElec = SEED_ELECTRICIANS[(i + 6) % SEED_ELECTRICIANS.length];
  } else if (i <= 80) {
    status = 'in_progress';
    assignedElec = SEED_ELECTRICIANS[(i + 8) % SEED_ELECTRICIANS.length];
  } else if (i <= 85) {
    status = 'on_hold';
    assignedElec = SEED_ELECTRICIANS[(i + 1) % SEED_ELECTRICIANS.length];
  } else if (i <= 95) {
    status = 'completed';
    assignedElec = SEED_ELECTRICIANS[(i + 3) % SEED_ELECTRICIANS.length];
  } else {
    status = 'closed';
    assignedElec = SEED_ELECTRICIANS[(i + 5) % SEED_ELECTRICIANS.length];
  }

  const submittedDate = new Date(Date.now() - (105 - i) * 3600000 * 4).toISOString();

  const req: ServiceRequest = {
    id: reqId,
    customerId: custUser.id,
    customerName: custUser.name,
    customerType: custUser.customerCategory || 'individual',
    customerPhone: custUser.phone,
    customerEmail: custUser.email,
    title,
    description: `Reported issue: ${title}. Observed in ${locality.name}, Mysuru. Customer requested inspection by certified technician.`,
    category,
    priority,
    location,
    preferredDate: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    preferredTimeWindow: i % 2 === 0 ? '09:00 - 12:00' : '14:00 - 17:00',
    attachments: [
      'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600',
    ],
    status,
    submittedAt: submittedDate,
    validatedAt: status !== 'submitted' && status !== 'under_review' ? submittedDate : undefined,
    validationNotes: status !== 'submitted' ? 'Verified CHESCOM safety standards confirmed.' : undefined,
    associatedJobId: status !== 'submitted' && status !== 'under_review' ? jobId : undefined,
  };
  SEED_SERVICE_REQUESTS.push(req);

  if (status !== 'submitted' && status !== 'under_review') {
    const requiredSkills: string[] = [];
    if (category === 'power_outage') requiredSkills.push('High Voltage Systems', 'Panel & Breaker Upgrades');
    else if (category === 'equipment_failure') requiredSkills.push('Emergency Generators', 'Industrial Wiring');
    else if (category === 'wiring_fault') requiredSkills.push('Cable Fault Diagnostics', 'Thermal Imaging Inspection');
    else if (category === 'panel_breaker') requiredSkills.push('Panel & Breaker Upgrades');
    else requiredSkills.push('Residential Wiring', 'Commercial Lighting');

    const requiredEquipment: string[] = [];
    if (priority === 'emergency' || category === 'power_outage') requiredEquipment.push('Insulated Tool Set (1000V)');
    if (category === 'equipment_failure') requiredEquipment.push('Industrial Generator Diagnostic Kit');
    if (category === 'wiring_fault') requiredEquipment.push('Digital Cable Fault Locator');

    const jobTimeline: JobTimelineEvent[] = [
      {
        status: 'submitted',
        timestamp: submittedDate,
        updatedBy: custUser.name,
        role: 'customer',
        notes: 'Service request registered via Mysuru portal',
      },
      {
        status: 'validated',
        timestamp: new Date(new Date(submittedDate).getTime() + 1800000).toISOString(),
        updatedBy: 'Automated Assessment Engine',
        role: 'supervisor',
        notes: 'Automated assessment verified CHESCOM regulatory safety guidelines.',
      },
    ];

    if (assignedElec) {
      jobTimeline.push({
        status: 'assigned',
        timestamp: new Date(new Date(submittedDate).getTime() + 3600000).toISOString(),
        updatedBy: 'Automated Scheduling Engine',
        role: 'supervisor',
        notes: `Automatically assigned to ${assignedElec.name} based on technical skill match and ${locality.name} proximity.`,
      });
    }

    if (status === 'completed' || status === 'closed') {
      jobTimeline.push({
        status: 'completed',
        timestamp: new Date(new Date(submittedDate).getTime() + 14400000).toISOString(),
        updatedBy: assignedElec ? assignedElec.name : 'Field Technician',
        role: 'technician',
        notes: 'Work completed. Replaced tripped circuit breaker and verified earthing resistance under 2 Ohms.',
      });
    }

    const job: Job = {
      id: jobId,
      requestId: reqId,
      title,
      description: req.description,
      category,
      priority,
      status,
      location,
      customerId: custUser.id,
      customerName: custUser.name,
      customerPhone: custUser.phone,
      estimatedDurationHours: estHours,
      requiredSkills,
      requiredEquipment,
      serviceDeadline: new Date(Date.now() + (priority === 'emergency' ? 7200000 : 86400000)).toISOString(),
      preferredTimeWindow: req.preferredTimeWindow,
      assignedElectricianId: assignedElec?.id || null,
      assignedElectricianName: assignedElec?.name || null,
      scheduledStartTime: assignedElec ? '09:30 AM IST' : undefined,
      scheduledEndTime: assignedElec ? '11:45 AM IST' : undefined,
      dispatchType: 'automatic',
      isOverdue: i % 14 === 0,
      slaRisk: i % 14 === 0 ? 'breached' : i % 9 === 0 ? 'warning' : 'normal',
      timeline: jobTimeline,
      completionReport: (status === 'completed' || status === 'closed') ? {
        workPerformed: 'Tested sub-panel voltage drop, replaced faulty 60A dual-pole breaker, torqued lugs to spec (45 in-lbs), conducted thermal re-scan.',
        faultIdentified: 'Arcing observed at terminal A lug due to thermal vibration looseness.',
        materialsUsed: ['Siemens 60A Dual-Pole Breaker', 'Antioxidant paste', 'Heat shrink sleeves (4 AWG)'],
        notes: 'Zero voltage leakage measured post-installation. Earthing impedance tested at 1.8 Ohms.',
        beforePhotos: ['https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600'],
        afterPhotos: ['https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=600'],
        completionTimestamp: new Date(new Date(submittedDate).getTime() + 14400000).toISOString(),
        signedOffByElectrician: assignedElec?.name || 'Pradeep Hegde',
      } : undefined,
      feedback: (status === 'completed' || status === 'closed') ? {
        rating: 5,
        comments: 'Prompt arrival in Mysuru and resolved the fault quickly. Very professional.',
        submittedAt: new Date(new Date(submittedDate).getTime() + 18000000).toISOString(),
      } : undefined,
      createdAt: submittedDate,
      updatedAt: new Date().toISOString(),
    };

    SEED_JOBS.push(job);
  }
}

// 4. APPROVALS & ESCALATIONS
export const SEED_APPROVALS: ApprovalRequest[] = [
  {
    id: 'APP-2026-001',
    title: 'Automated Schedule Re-balancing: Tech Pradeep Hegde Absence',
    category: 'high_impact_schedule',
    relatedJobId: 'JOB-2026-4045',
    relatedDisruptionId: 'DISR-2026-01',
    details: 'Technician Pradeep Hegde reported vehicle breakdown on Hunsur Road. Automated recovery engine re-balanced 4 assigned jobs to standby technicians in Kuvempunagar & Saraswathipuram.',
    requestedBy: 'Automated Recovery Engine',
    requesterRole: 'supervisor',
    currentStatus: 'approved',
    impactLevel: 'critical',
    submittedAt: new Date(Date.now() - 3600000 * 2).toISOString(),
    reviewedBy: 'Meera Kulkarni',
    reviewedAt: new Date(Date.now() - 3600000).toISOString(),
    reviewNotes: 'Verified automated reassignment preserves Cauvery Hospital emergency SLA.',
  },
  {
    id: 'APP-2026-002',
    title: 'SLA Extension for Hebbal 480V Industrial Feeder Diagnosis',
    category: 'major_sla_exception',
    relatedJobId: 'JOB-2026-4072',
    details: 'Heavy 480V industrial switchgear in Hebbal Industrial Area requires full CHESCOM isolation. Customer requested delaying repair from 2 PM to 10 PM night shutdown to avoid factory halt.',
    requestedBy: 'Automated Recovery Engine',
    requesterRole: 'supervisor',
    currentStatus: 'pending',
    impactLevel: 'high',
    submittedAt: new Date(Date.now() - 3600000 * 5).toISOString(),
  },
];

export const SEED_ESCALATIONS: EscalationAlert[] = [
  {
    id: 'ESC-2026-101',
    jobId: 'JOB-2026-4014',
    title: 'SLA Warning on Hospital Emergency Line',
    description: 'Ticket approaching 45-minute target in Kuvempunagar. Standby technician auto-alerted.',
    severity: 'critical',
    sourceRole: 'supervisor',
    raisedBy: 'Automated SLA Monitor',
    assignedToRole: 'operations',
    status: 'open',
    createdAt: new Date(Date.now() - 2400000).toISOString(),
  },
  {
    id: 'ESC-2026-102',
    jobId: 'JOB-2026-4028',
    title: 'Specialized Arc Flash PPE Required',
    description: 'Assigned tech in Hootagalli requires Cat 4 arc flash PPE verification prior to transformer test.',
    severity: 'high',
    sourceRole: 'technician',
    raisedBy: 'Manjunath Bhat',
    assignedToRole: 'operations',
    status: 'open',
    createdAt: new Date(Date.now() - 5400000).toISOString(),
  },
];

export const SEED_DISRUPTIONS: DisruptionRecord[] = [
  {
    id: 'DISR-2026-01',
    type: 'technician_delay',
    title: 'Traffic delay on Sayyaji Rao Road corridor',
    description: 'Procession near Mysore Palace created detour. En route technician delay handled via automated reroute.',
    affectedElectricianId: 'elec-2',
    affectedJobIds: ['JOB-2026-1002'],
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    status: 'resolved',
    proposedResolution: {
      reassignments: [
        {
          jobId: 'JOB-2026-1002',
          jobTitle: 'Commercial Switchgear Inspection',
          newElectricianId: 'elec-3',
          newElectricianName: 'Manjunath Bhat',
          originalTime: '10:00',
          newTime: '10:20',
          reason: 'Autonomous reroute via alternate corridor',
          requiresApproval: false,
        },
      ],
      impactSummary: 'Resolved with zero SLA violation',
    },
  },
  {
    id: 'DISR-2026-02',
    type: 'equipment_failure',
    title: 'Vehicle puncture on Hebbal Industrial Outer Ring Road',
    description: 'Utility van breakdown. Emergency generator job reallocated to standby technician in Vijayanagar.',
    affectedElectricianId: 'elec-4',
    affectedJobIds: ['JOB-2026-1004'],
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    status: 'resolved',
  },
  {
    id: 'DISR-2026-03',
    type: 'emergency_job_injection',
    title: 'Overhead transformer flashover near Kuvempunagar Depot',
    description: 'CHESCOM distribution feeder trip. Automatic rescheduling engine dispatched priority squad.',
    affectedElectricianId: 'elec-1',
    affectedJobIds: ['JOB-2026-1001'],
    timestamp: new Date(Date.now() - 1800000).toISOString(),
    status: 'detected',
  },
];

// 5. NOTIFICATIONS
export const SEED_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'NOTIF-01',
    targetRole: 'supervisor',
    title: 'Automated Assignment Completed',
    message: 'REQ-2026-1001 automatically scheduled to Pradeep Hegde (Match score 94%).',
    type: 'info',
    linkUrl: '/supervisor/jobs',
    timestamp: new Date(Date.now() - 600000).toISOString(),
    isRead: false,
  },
  {
    id: 'NOTIF-02',
    targetRole: 'technician',
    title: 'New Job Dispatched',
    message: 'You have been automatically assigned to JOB-2026-4045 in Saraswathipuram.',
    type: 'info',
    linkUrl: '/technician/jobs',
    timestamp: new Date(Date.now() - 1800000).toISOString(),
    isRead: false,
  },
  {
    id: 'NOTIF-03',
    targetRole: 'supervisor',
    title: 'SLA Adherence Alert',
    message: 'JOB-2026-4014 is within 15 minutes of SLA target.',
    type: 'warning',
    linkUrl: '/supervisor/overview',
    timestamp: new Date(Date.now() - 2700000).toISOString(),
    isRead: false,
  },
  {
    id: 'NOTIF-04',
    targetRole: 'customer',
    title: 'Technician Assigned',
    message: 'Technician Pradeep Hegde has been automatically dispatched for your Saraswathipuram service request.',
    type: 'success',
    linkUrl: '/customer/requests',
    timestamp: new Date(Date.now() - 1200000).toISOString(),
    isRead: false,
  },
];

// 6. AUDIT LOGS
export const SEED_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 'AUD-901',
    userId: 'usr-tech-1',
    userName: 'Pradeep Hegde',
    userRole: 'technician',
    action: 'STATUS_TRANSITION',
    entityType: 'job',
    entityId: 'JOB-2026-4045',
    previousValue: 'assigned',
    newValue: 'en_route',
    reason: 'Technician departed for Saraswathipuram client site',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'AUD-902',
    userId: 'system',
    userName: 'Automated Scheduling Engine',
    userRole: 'supervisor',
    action: 'AUTO_SCHEDULE_OPTIMIZED',
    entityType: 'schedule',
    entityId: 'JOB-2026-4045',
    previousValue: 'unassigned',
    newValue: 'assigned',
    reason: 'Automated algorithm recommended Pradeep Hegde (Match Score: 94.2%, Distance: 3.4 km)',
    timestamp: new Date(Date.now() - 9600000).toISOString(),
  },
  {
    id: 'AUD-903',
    userId: 'usr-sup-1',
    userName: 'Meera Kulkarni',
    userRole: 'supervisor',
    action: 'SUPERVISOR_OBSERVATION',
    entityType: 'schedule',
    entityId: 'GRID-MYSURU-CENTRAL',
    previousValue: 'nominal',
    newValue: 'monitored',
    reason: 'Supervised automated re-balancing following Hunsur road transit delay',
    timestamp: new Date(Date.now() - 72000000).toISOString(),
  },
];

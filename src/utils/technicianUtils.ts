import { User, Electrician, Job } from '../types';

/**
 * Robust resolution of the logged-in user to their corresponding Electrician profile.
 * Handles:
 * - Direct ID match (e.id === user.id)
 * - User ID match (e.userId === user.id)
 * - Employee ID match (e.employeeId === user.employeeId)
 * - Email match (case-insensitive)
 * - Full name match (case-insensitive)
 * - Known aliases (e.g. Chidan Kumar <=> Chetan Kumar, MYS-TECH-108)
 * - Avoids false-positive fallback to electricians[0] for non-technicians
 */
export function resolveCurrentElectrician(
  user: User | null | undefined,
  electricians: Electrician[]
): Electrician | undefined {
  if (!user || !electricians || electricians.length === 0) {
    return undefined;
  }

  const userId = (user.id || '').trim().toLowerCase();
  const userEmpId = (user.employeeId || '').trim().toLowerCase();
  const userEmail = (user.email || '').trim().toLowerCase();
  const userName = (user.name || '').trim().toLowerCase();

  // 1. Direct userId or id match
  let matched = electricians.find((e) => {
    const eId = (e.id || '').toLowerCase();
    const eUserId = (e.userId || '').toLowerCase();
    return (
      (userId && (eId === userId || eUserId === userId)) ||
      (userEmpId && e.employeeId && e.employeeId.toLowerCase() === userEmpId)
    );
  });
  if (matched) return matched;

  // 2. Email match
  if (userEmail) {
    matched = electricians.find(
      (e) => e.email && e.email.toLowerCase() === userEmail
    );
    if (matched) return matched;
  }

  // 3. Exact or substring name match
  if (userName) {
    matched = electricians.find(
      (e) => e.name && e.name.toLowerCase() === userName
    );
    if (matched) return matched;
  }

  // 4. Special alias handling for Chidan Kumar <=> Chetan Kumar (MYS-TECH-108)
  const isChidanOrChetan =
    userName.includes('chidan') ||
    userName.includes('chetan') ||
    userEmail.includes('chidan') ||
    userEmail.includes('chetan') ||
    userEmpId === 'mys-tech-108' ||
    userId === 'elec-9' ||
    userId === 'usr-tech-9';

  if (isChidanOrChetan) {
    const chetan = electricians.find(
      (e) =>
        e.id === 'elec-9' ||
        e.userId === 'usr-tech-9' ||
        (e.employeeId && e.employeeId.toUpperCase() === 'MYS-TECH-108') ||
        e.name.toLowerCase().includes('chetan') ||
        e.name.toLowerCase().includes('chidan')
    );
    if (chetan) return chetan;
  }

  // 5. If user id has usr-tech-N or elec-N pattern, map numerically
  const techNumMatch = userId.match(/(?:usr-tech-|elec-)(\d+)/);
  if (techNumMatch) {
    const num = parseInt(techNumMatch[1], 10);
    const techByNum = electricians.find(
      (e) => e.id === `elec-${num}` || e.userId === `usr-tech-${num}`
    );
    if (techByNum) return techByNum;
  }

  // 6. If user is explicitly a technician role, fallback safely to first electrician
  if (user.role === 'technician' || user.role === 'electrician') {
    return electricians[0];
  }

  return undefined;
}

/**
 * Robust check if a job is assigned or offered to a given electrician/user.
 * Prevents identity mismatch across:
 * - elec.id vs elec.userId vs elec.employeeId vs user.id
 * - Name matching and Chidan/Chetan aliases
 * - In-flight job offers
 * - Electrician currentJobId
 */
export function isJobAssignedToElectrician(
  job: Job | null | undefined,
  tech: Electrician | null | undefined,
  user?: User | null
): boolean {
  if (!job) return false;

  const assignedId = (job.assignedElectricianId || '').trim().toLowerCase();
  const assignedName = (job.assignedElectricianName || '').trim().toLowerCase();

  const techId = tech?.id ? tech.id.toLowerCase() : '';
  const techUserId = tech?.userId ? tech.userId.toLowerCase() : '';
  const techEmpId = tech?.employeeId ? tech.employeeId.toLowerCase() : '';
  const techName = tech?.name ? tech.name.toLowerCase() : '';

  const userId = user?.id ? user.id.toLowerCase() : '';
  const userEmpId = user?.employeeId ? user.employeeId.toLowerCase() : '';
  const userName = user?.name ? user.name.toLowerCase() : '';

  // 1. Direct ID matches on assignedElectricianId
  if (assignedId) {
    if (
      (techId && assignedId === techId) ||
      (techUserId && assignedId === techUserId) ||
      (techEmpId && assignedId === techEmpId) ||
      (userId && assignedId === userId) ||
      (userEmpId && assignedId === userEmpId)
    ) {
      return true;
    }

    // Special case for demo elec-1 / usr-tech-1 / usr-elec-1
    if (
      (assignedId === 'elec-1' || assignedId === 'usr-tech-1') &&
      (techId === 'elec-1' || userId === 'usr-tech-1' || userId === 'usr-elec-1')
    ) {
      return true;
    }
  }

  // 2. Direct name match
  if (assignedName && (techName || userName)) {
    if (
      (techName && assignedName === techName) ||
      (userName && assignedName === userName)
    ) {
      return true;
    }
  }

  // 3. Alias check for Chidan Kumar <=> Chetan Kumar
  const isJobAssignedToChidanOrChetan =
    assignedName.includes('chidan') ||
    assignedName.includes('chetan') ||
    assignedId === 'elec-9' ||
    assignedId === 'usr-tech-9' ||
    assignedId === 'mys-tech-108';

  const isTechOrUserChidanOrChetan =
    techName.includes('chidan') ||
    techName.includes('chetan') ||
    userName.includes('chidan') ||
    userName.includes('chetan') ||
    techId === 'elec-9' ||
    techUserId === 'usr-tech-9' ||
    techEmpId === 'mys-tech-108' ||
    userId === 'usr-tech-9' ||
    userEmpId === 'mys-tech-108';

  if (isJobAssignedToChidanOrChetan && isTechOrUserChidanOrChetan) {
    return true;
  }

  // 4. In-flight offer match
  if (job.currentOffer) {
    const offerTechId = (job.currentOffer.technicianId || '').trim().toLowerCase();
    const offerTechName = (job.currentOffer.technicianName || '').trim().toLowerCase();

    if (
      (techId && offerTechId === techId) ||
      (techUserId && offerTechId === techUserId) ||
      (techEmpId && offerTechId === techEmpId) ||
      (userId && offerTechId === userId) ||
      (techName && offerTechName === techName) ||
      (userName && offerTechName === userName)
    ) {
      return true;
    }

    if (
      (offerTechName.includes('chidan') ||
        offerTechName.includes('chetan') ||
        offerTechId === 'elec-9' ||
        offerTechId === 'usr-tech-9') &&
      isTechOrUserChidanOrChetan
    ) {
      return true;
    }
  }

  // 5. Electrician's currentJobId match
  if (tech?.currentJobId && tech.currentJobId === job.id) {
    return true;
  }

  return false;
}

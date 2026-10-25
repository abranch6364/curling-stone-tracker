import { useBreakpointValue } from "@chakra-ui/react";

// Whether the screen is phone sized: narrower than Chakra's md breakpoint (768px). Components use this where a
// phone behaves differently (e.g. the sheet's orientation); styling alone uses responsive style props instead.
const useIsPhone = () => useBreakpointValue({ base: true, md: false }, { ssr: false }) ?? false;

export default useIsPhone;

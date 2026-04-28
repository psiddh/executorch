/* Place the model PTE blob in DDR so it does not overflow the small
 * ITCM (FLASH) and ISRAM (RAM) regions on Corstone FVP boards.
 * The Ethos-U NPU can DMA from DDR on these platforms.
 */
SECTION_DATA_PROLOGUE(network_model_sec,,)
{
    . = ALIGN(16);
    *(.network_model_sec)
    *(.network_model_sec.*)
} GROUP_DATA_LINK_IN(MODEL_DDR, MODEL_DDR)

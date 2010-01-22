<?xml version="1.0" encoding="UTF-8"?>
<!--
libxslt needs explicit namespaces
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:marc="http://www.loc.gov/MARC21/slim"  version="1.0">

<xsl:template match="text()"/>

<xsl:template match="/marc:record">
        <xsl:apply-templates/>
</xsl:template>

<xsl:template match="marc:datafield[@tag='245']">
<xsl:value-of select="marc:subfield[@code='a']"/>
</xsl:template>

</xsl:stylesheet>
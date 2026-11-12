Name:		kotlin-assignment-compiler-plugin-embeddable
Version:	2.4.21
Release:	1
Summary:	Kotlin assignment compiler plugin
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/JetBrains/kotlin
# Kotlin tag v2.4.21, plugins/assign-plugin.
# Artifact org.jetbrains.kotlin:kotlin-assignment-compiler-plugin-embeddable.
# This is the compiler plugin, not the kotlin-assignment Gradle subplugin.
# The published jar is the plugin classes. It does not shade the compiler.
# kotlinc 2.0.21 cannot parse context parameters or load several 2.4 FIR
# signatures. Those types are compile-only overlays and are not installed.
# FIR overlays are compiled one file at a time. Combining them makes kotlinc
# 2.0.21 crash while lowering FirSimpleFunctionImpl. The CLI module is
# compiled without the FirExtensionRegistrar overlay so registerExtension
# binds to the real companion.
Source0:	kotlin-assignment-compiler-plugin-embeddable-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-21-openjdk-devel
BuildRequires:	kotlin = 2.0.21
BuildRequires:	kotlin-stdlib >= 2.4.21-2
BuildRequires:	objectweb-asm
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem

%description
org.jetbrains.kotlin:kotlin-assignment-compiler-plugin-embeddable %{version}.
The assignment Kotlin compiler plugin from tag v2.4.21, compiled with the
installed kotlinc 2.0.21.

%prep
%autosetup -n kotlin-assignment-compiler-plugin-embeddable-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
STDLIB=%{_javadir}/kotlin-stdlib-%{version}.jar
COMPILER=/usr/share/kotlin/lib/kotlin-compiler.jar
ASM=/usr/share/java/asm.jar
test -s "$STDLIB"
test -s "$COMPILER"
test -s "$ASM"
/bin/rm -rf gen-classes fn-classes api-classes ktsrc-classes kind-classes k2-classes cli-classes stage
mkdir -p gen-classes fn-classes
javac -proc:none -cp "$ASM" -d gen-classes overlay/gen/GenOverlays.java
java -cp "gen-classes:$ASM" GenOverlays \
	"$PWD/fn-classes/org/jetbrains/kotlin/fir/declarations/FirNamedFunction.class" \
	"$PWD/fn-classes/org/jetbrains/kotlin/fir/symbols/impl/FirRegularPropertySymbol.class" \
	"$PWD/fn-classes/org/jetbrains/kotlin/KtFakeSourceElementKind\$AssignmentPluginAltered.class"
test -s fn-classes/org/jetbrains/kotlin/fir/declarations/FirNamedFunction.class
test -s fn-classes/org/jetbrains/kotlin/fir/symbols/impl/FirRegularPropertySymbol.class
test -s "fn-classes/org/jetbrains/kotlin/KtFakeSourceElementKind\$AssignmentPluginAltered.class"

kc() {
	local name out cp
	name="$1"
	out="$2"
	cp="$3"
	shift 3
	/bin/rm -rf "$out"
	mkdir -p "$out"
	printf '%s\n' "$@" > "$name.files"
	kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -Xcontext-receivers -no-stdlib -jdk-home "$JAVA_HOME" \
		-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
		-module-name "assignov-$name" \
		-classpath "$cp" \
		-d "$out" @"$name.files" < /dev/null
}

kc api api-classes "$STDLIB:$COMPILER" \
	overlay/api/org/jetbrains/kotlin/compiler/plugin/CompilerPluginRegistrar.kt \
	overlay/api/org/jetbrains/kotlin/extensions/ExtensionPointDescriptor.kt
kc ktsrc ktsrc-classes "$STDLIB:$COMPILER" \
	overlay/fir/org/jetbrains/kotlin/KtSourceElement.kt \
	overlay/fir/org/jetbrains/kotlin/KtSourceElementOffsetStrategy.kt

BASE="ktsrc-classes:api-classes:fn-classes:$STDLIB:$COMPILER"
kc direct direct-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/declarations/DirectDeclarationsAccess.kt
kc tosymbol tosymbol-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/resolve/ToSymbolUtils.kt
kc typeutils typeutils-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/types/TypeUtils.kt
kc exprutil exprutil-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/expressions/FirExpressionUtil.kt
kc builder builder-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/expressions/builder/FirPropertyAccessExpressionBuilder.kt
kc diagcontainer diagcontainer-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/diagnostics/KtDiagnosticsContainer.kt
kc rendermap rendermap-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/diagnostics/KtDiagnosticFactoryToRendererMap.kt
kc declchecker declchecker-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/analysis/checkers/declaration/FirDeclarationChecker.kt
kc exprchecker exprchecker-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/analysis/checkers/expression/FirExpressionChecker.kt
kc firextutil firextutil-classes "$BASE" \
	overlay/fir/org/jetbrains/kotlin/compiler/plugin/FirExtensionRegistrarConfigurationUtil.kt
kc declcheckers declcheckers-classes "declchecker-classes:$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/analysis/checkers/declaration/DeclarationCheckers.kt
kc provider provider-classes "diagcontainer-classes:$BASE" \
	overlay/fir/org/jetbrains/kotlin/diagnostics/DiagnosticFactory0DelegateProvider.kt
kc registrar registrar-classes "diagcontainer-classes:$BASE" \
	overlay/fir/org/jetbrains/kotlin/fir/extensions/FirExtensionRegistrar.kt

javac -proc:none --release 8 -cp "fn-classes:$COMPILER" -d kind-classes \
	plugins/assign-plugin/assign-plugin.k2/src/org/jetbrains/kotlin/assignment/plugin/k2/AssignmentPluginAlteredKind.java
test -s kind-classes/org/jetbrains/kotlin/assignment/plugin/k2/AssignmentPluginAlteredKind.class

K2CP="api-classes:fn-classes:ktsrc-classes:kind-classes"
K2CP="$K2CP:direct-classes:tosymbol-classes:typeutils-classes:exprutil-classes:builder-classes"
K2CP="$K2CP:diagcontainer-classes:rendermap-classes:declchecker-classes:exprchecker-classes"
K2CP="$K2CP:firextutil-classes:declcheckers-classes:provider-classes:registrar-classes"
K2CP="$K2CP:$STDLIB:$COMPILER"
find plugins/assign-plugin/assign-plugin.k2/src -name '*.kt' | sort > k2.files
test "$(wc -l < k2.files)" = 8
/bin/rm -rf k2-classes
mkdir -p k2-classes
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -Xcontext-receivers -no-stdlib -jdk-home "$JAVA_HOME" \
	-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
	-module-name kotlin-assignment-compiler-plugin-k2 \
	-classpath "$K2CP" \
	-d k2-classes @k2.files < /dev/null

find plugins/assign-plugin/assign-plugin.cli/src plugins/assign-plugin/assign-plugin.common/src -name '*.kt' | sort > cli.files
test "$(wc -l < cli.files)" = 2
/bin/rm -rf cli-classes
mkdir -p cli-classes
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xwhen-guards -Xjvm-default=all -Xcontext-receivers -no-stdlib -jdk-home "$JAVA_HOME" \
	-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
	-module-name kotlin-assignment-compiler-plugin-cli \
	-classpath "k2-classes:api-classes:firextutil-classes:$STDLIB:$COMPILER" \
	-d cli-classes @cli.files < /dev/null

n=$(find k2-classes cli-classes kind-classes -name '*.class' | wc -l | tr -d ' ')
test "$n" = 21

javap -p -s -classpath k2-classes org.jetbrains.kotlin.assignment.plugin.k2.diagnostics.FirAssignmentPluginFunctionChecker > function.javap
grep -F -q 'check(org.jetbrains.kotlin.fir.analysis.checkers.context.CheckerContext, org.jetbrains.kotlin.diagnostics.DiagnosticReporter, org.jetbrains.kotlin.fir.declarations.FirNamedFunction)' function.javap
javap -c -p -classpath k2-classes org.jetbrains.kotlin.assignment.plugin.k2.diagnostics.FirAssignmentPluginFunctionChecker > function.c.javap
grep -F -q 'FirNamedFunction.getName:()Lorg/jetbrains/kotlin/name/Name;' function.c.javap
grep -F -q 'TypeUtilsKt.toRegularClassSymbol:(Lorg/jetbrains/kotlin/fir/types/FirTypeRef;Lorg/jetbrains/kotlin/fir/FirSession;)Lorg/jetbrains/kotlin/fir/symbols/impl/FirRegularClassSymbol;' function.c.javap
grep -F -q 'ToSymbolUtilsKt.toRegularClassSymbol:(Lorg/jetbrains/kotlin/fir/types/ConeKotlinType;)Lorg/jetbrains/kotlin/fir/symbols/impl/FirRegularClassSymbol;' function.c.javap
javap -c -p -classpath k2-classes org.jetbrains.kotlin.assignment.plugin.k2.FirAssignmentPluginAssignAltererExtension > alterer.c.javap
grep -F -q 'FirExpressionUtilKt.getContextArguments:(Lorg/jetbrains/kotlin/fir/expressions/FirVariableAssignment;)Ljava/util/List;' alterer.c.javap
grep -F -q 'FirPropertyAccessExpressionBuilder.getContextArguments:()Ljava/util/List;' alterer.c.javap
grep -F -q 'FirPropertyAccessExpressionBuilder.setCalleeReference:(Lorg/jetbrains/kotlin/fir/references/FirNamedReference;)V' alterer.c.javap
grep -F -q 'KtSourceElementKt.fakeElement$default:(Lorg/jetbrains/kotlin/KtSourceElement;Lorg/jetbrains/kotlin/KtFakeSourceElementKind;Lorg/jetbrains/kotlin/KtSourceElementOffsetStrategy;ILjava/lang/Object;)Lorg/jetbrains/kotlin/KtSourceElement;' alterer.c.javap
javap -c -p -classpath k2-classes org.jetbrains.kotlin.assignment.plugin.k2.FirAssignmentPluginExtensionRegistrar > exreg.c.javap
grep -F -q 'FirExtensionRegistrar$ExtensionRegistrarContext.registerDiagnosticContainers:([Lorg/jetbrains/kotlin/diagnostics/KtDiagnosticsContainer;)V' exreg.c.javap
grep -F -q 'FirExtensionRegistrar$ExtensionRegistrarContext.plusAssignExpressionAltererExtension:(Lkotlin/jvm/functions/Function1;)V' exreg.c.javap
javap -c -p -classpath k2-classes org.jetbrains.kotlin.assignment.plugin.k2.diagnostics.FirErrorsAssignmentPlugin > errors.c.javap
grep -F -q 'DiagnosticFactory0DelegateProvider."<init>":(Lorg/jetbrains/kotlin/diagnostics/Severity;Lorg/jetbrains/kotlin/diagnostics/AbstractSourceElementPositioningStrategy;Lkotlin/reflect/KClass;Lorg/jetbrains/kotlin/diagnostics/KtDiagnosticsContainer;)V' errors.c.javap
javap -c -p -classpath cli-classes org.jetbrains.kotlin.assignment.plugin.AssignmentComponentRegistrar > registrar.c.javap
grep -F -q 'FirExtensionRegistrarConfigurationUtilKt.registerExtension:(Lorg/jetbrains/kotlin/compiler/plugin/CompilerPluginRegistrar$ExtensionStorage;Lorg/jetbrains/kotlin/fir/extensions/FirExtensionRegistrar$Companion;Lorg/jetbrains/kotlin/fir/extensions/FirExtensionRegistrar;)V' registrar.c.javap
javap -c -p -classpath kind-classes org.jetbrains.kotlin.assignment.plugin.k2.AssignmentPluginAlteredKind > kind.c.javap
grep -F -q 'KtFakeSourceElementKind$AssignmentPluginAltered.INSTANCE:Lorg/jetbrains/kotlin/KtFakeSourceElementKind$AssignmentPluginAltered;' kind.c.javap

mkdir -p stage/META-INF/services
/bin/cp -a k2-classes/. stage/
/bin/cp -a cli-classes/. stage/
/bin/cp -a kind-classes/. stage/
/bin/cp -a plugins/assign-plugin/assign-plugin.cli/resources/META-INF/services/. stage/META-INF/services/
cat > manifest.mf << 'EOF'
Manifest-Version: 1.0
Automatic-Module-Name: kotlin.assignment.compiler.plugin
Created-By: OpenMandriva

EOF
jar cfm kotlin-assignment-compiler-plugin-embeddable.jar manifest.mf -C stage .
jar tf kotlin-assignment-compiler-plugin-embeddable.jar > jar.list
cat > forbidden.list << 'EOF'
org/jetbrains/kotlin/fir/declarations/FirNamedFunction.class
org/jetbrains/kotlin/fir/symbols/impl/FirRegularPropertySymbol.class
org/jetbrains/kotlin/fir/declarations/DirectDeclarationsAccess.class
org/jetbrains/kotlin/fir/analysis/checkers/declaration/FirDeclarationChecker.class
org/jetbrains/kotlin/fir/analysis/checkers/declaration/DeclarationCheckers.class
org/jetbrains/kotlin/fir/analysis/checkers/expression/FirExpressionChecker.class
org/jetbrains/kotlin/fir/extensions/FirExtensionRegistrar.class
org/jetbrains/kotlin/fir/extensions/FirExtensionRegistrar$Companion.class
org/jetbrains/kotlin/fir/extensions/FirExtensionRegistrar$ExtensionRegistrarContext.class
org/jetbrains/kotlin/diagnostics/KtDiagnosticsContainer.class
org/jetbrains/kotlin/diagnostics/DiagnosticFactory0DelegateProvider.class
org/jetbrains/kotlin/diagnostics/KtDiagnosticFactoryToRendererMapKt.class
org/jetbrains/kotlin/fir/types/TypeUtilsKt.class
org/jetbrains/kotlin/fir/resolve/ToSymbolUtilsKt.class
org/jetbrains/kotlin/fir/expressions/FirExpressionUtilKt.class
org/jetbrains/kotlin/fir/expressions/builder/FirPropertyAccessExpressionBuilder.class
org/jetbrains/kotlin/KtFakeSourceElementKind$AssignmentPluginAltered.class
org/jetbrains/kotlin/KtSourceElementKt.class
org/jetbrains/kotlin/KtSourceElementOffsetStrategy.class
org/jetbrains/kotlin/compiler/plugin/CompilerPluginRegistrar.class
org/jetbrains/kotlin/compiler/plugin/FirExtensionRegistrarConfigurationUtilKt.class
org/jetbrains/kotlin/extensions/ExtensionPointDescriptor.class
EOF
while IFS= read -r bad; do
	if grep -F -qx "$bad" jar.list; then
		echo "forbidden $bad"
		exit 1
	fi
done < forbidden.list
grep -F -qx 'META-INF/services/org.jetbrains.kotlin.compiler.plugin.CompilerPluginRegistrar' jar.list
grep -F -qx 'META-INF/services/org.jetbrains.kotlin.compiler.plugin.CommandLineProcessor' jar.list
grep -F -qx 'org/jetbrains/kotlin/assignment/plugin/AssignmentCommandLineProcessor.class' jar.list
grep -F -qx 'org/jetbrains/kotlin/assignment/plugin/AssignmentComponentRegistrar.class' jar.list
grep -F -qx 'org/jetbrains/kotlin/assignment/plugin/k2/AssignmentPluginAlteredKind.class' jar.list
grep -F -qx 'org/jetbrains/kotlin/assignment/plugin/k2/FirAssignmentPluginExtensionRegistrar.class' jar.list
grep -F -qx 'org/jetbrains/kotlin/assignment/plugin/k2/FirAssignmentPluginAssignAltererExtension.class' jar.list
mkdir -p svc
( cd svc && jar xf ../kotlin-assignment-compiler-plugin-embeddable.jar META-INF/services )
grep -F -qx 'org.jetbrains.kotlin.assignment.plugin.AssignmentCommandLineProcessor' svc/META-INF/services/org.jetbrains.kotlin.compiler.plugin.CommandLineProcessor
grep -F -qx 'org.jetbrains.kotlin.assignment.plugin.AssignmentComponentRegistrar' svc/META-INF/services/org.jetbrains.kotlin.compiler.plugin.CompilerPluginRegistrar
desc=$(jar --describe-module --file kotlin-assignment-compiler-plugin-embeddable.jar)
printf '%s\n' "$desc" | grep -F -qx 'kotlin.assignment.compiler.plugin automatic'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	echo "describe failed"
	exit 1
fi
cat > kotlin-assignment-compiler-plugin-embeddable.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.jetbrains.kotlin</groupId>
  <artifactId>kotlin-assignment-compiler-plugin-embeddable</artifactId>
  <version>%{version}</version>
  <name>kotlin-assignment-compiler-plugin-embeddable</name>
  <description>Kotlin assignment compiler plugin</description>
  <url>https://github.com/JetBrains/kotlin</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>%{version}</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact kotlin-assignment-compiler-plugin-embeddable.pom:kotlin-assignment-compiler-plugin-embeddable.jar \
	--file-name kotlin-assignment-compiler-plugin-embeddable \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/org.jetbrains.kotlin/kotlin-assignment-compiler-plugin-embeddable.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "kotlin-assignment-compiler-plugin-embeddable"' "$idx"
test -s %{buildroot}%{_javadir}/kotlin-assignment-compiler-plugin-embeddable.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/kotlin-assignment-compiler-plugin-embeddable.jar
STDLIB=%{_javadir}/kotlin-stdlib-%{version}.jar
COMPILER=/usr/share/kotlin/lib/kotlin-compiler.jar
test -s "$JAR"
test -s "$STDLIB"
test -s "$COMPILER"
mkdir -p check/out
cat > check/Probe.kt << 'EOF'
import org.jetbrains.kotlin.assignment.plugin.AssignmentCommandLineProcessor
import org.jetbrains.kotlin.assignment.plugin.AssignmentComponentRegistrar
import org.jetbrains.kotlin.assignment.plugin.AssignmentConfigurationKeys
import org.jetbrains.kotlin.compiler.plugin.AbstractCliOption
import org.jetbrains.kotlin.config.CompilerConfiguration

fun main() {
    val processor = AssignmentCommandLineProcessor()
    if (processor.pluginId != "org.jetbrains.kotlin.assignment") error("id " + processor.pluginId)
    val configuration = CompilerConfiguration()
    val option = AssignmentCommandLineProcessor.ANNOTATION_OPTION
    processor.processOption(option as AbstractCliOption, "com.example.Assign", configuration)
    val anns = configuration.get(AssignmentConfigurationKeys.ASSIGNMENT_ANNOTATION)
    if (anns != listOf("com.example.Assign")) error("anns " + anns)
    val registrar = AssignmentComponentRegistrar()
    if (registrar.pluginId != "org.jetbrains.kotlin.assignment") error("rid " + registrar.pluginId)
    if (!registrar.supportsK2) error("k2")
    val src = AssignmentCommandLineProcessor::class.java.protectionDomain.codeSource.location.path
    if (!src.endsWith("kotlin-assignment-compiler-plugin-embeddable.jar")) error("src " + src)
    println("assignment_compiler_plugin_ok " + processor.pluginId + " " + anns!!.single() + " " + registrar.supportsK2)
}
EOF
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 -no-stdlib -jdk-home "$JAVA_HOME" \
	-opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
	-cp "$JAR:$STDLIB:$COMPILER" -d check/out check/Probe.kt < /dev/null
java -cp "check/out:$JAR:$STDLIB:$COMPILER" ProbeKt > check/out.txt
cat check/out.txt
grep -F -qx 'assignment_compiler_plugin_ok org.jetbrains.kotlin.assignment com.example.Assign true' check/out.txt

%files -f .mfiles
%license license/LICENSE.txt
%doc license/NOTICE.txt

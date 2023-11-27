#!/usr/bin/env python3
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

from ruamel.yaml import YAML
import os
from os import walk
from io import StringIO

acceptedEnvs = [
        "NCCL_ALGO",
        "NCCL_COLLNET_ENABLE",
        "NCCL_COLLTRACE_LOCAL_SUBDIR",
        "NCCL_COMM_ID",
        "NCCL_CUDA_PATH",
        "NCCL_CROSS_NIC",
        "NCCL_DEBUG",
        "NCCL_DEBUG_FILE",
        "NCCL_DEBUG_SUBSYS",
        "NCCL_GRAPH_DUMP_FILE",
        "NCCL_GRAPH_FILE",
        "NCCL_HOSTID",
        "NCCL_IB_DISABLE",
        "NCCL_IB_GID_INDEX",
        "NCCL_IB_TC",
        "NCCL_IB_TIMEOUT",
        "NCCL_IB_QPS_PER_CONNECTION",
        "NCCL_LAUNCH_MODE",
        "NCCL_NET",
        "NCCL_NET_PLUGIN",
        "NCCL_NET_SHARED_COMMS",
        "NCCL_NSOCKS_PERTHREAD",
        "NCCL_PROTO",
        "NCCL_PROXY_PROFILE",
        "NCCL_PXN_DISABLE",
        "NCCL_P2P_LEVEL",
        "NCCL_SHM_DISABLE",
        "NCCL_SOCKET_FAMILY",
        "NCCL_SOCKET_IFNAME",
        "NCCL_SOCKET_NTHREADS",
        "NCCL_THREAD_THRESHOLDS",
        "NCCL_TOPO_DUMP_FILE",
        "NCCL_TOPO_FILE",
        "NCCL_TUNER_PLUGIN",
    ]

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


def loadCvarsFromFiles(filenames):
    stream = "cvars:\n"
    for file in filenames:
        f = open(file, 'r')
        lines = f.readlines()
        f.close()

        ready = False
        for line in lines:
            if line.find('END_NCCL_CVAR_INFO_BLOCK') != -1:
                ready = False
            if ready == True:
                stream += line
            if line.find('BEGIN_NCCL_CVAR_INFO_BLOCK') != -1:
                ready = True

    return YAML().load(stream)


@static_vars(counter = 0)
def indent(file, str_):
    str = str_.strip()
    if (str[0] == '}'):
        c = indent.counter - 1
    else:
        c = indent.counter
    spaces = ""
    for i in range(c):
        spaces += "  "
    file.write("%s%s\n" % (spaces, str))
    indent.counter += str.count('{') - str.count('}')


class basetype:
    def __init__(self, cvar):
        self.name = cvar['name']
        self.default = cvar['default']
        self.description = cvar['description']
        self.type = cvar['type']
        if 'choices' in cvar:
            self.choices = cvar['choices']
        else:
            self.choices = ""

    @staticmethod
    def utilfns(file):
        indent(file, "// trim from start (in place)")
        indent(file, "static inline void ltrim(std::string &s) {")
        indent(file, "s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](unsigned char ch) {")
        indent(file, "return !std::isspace(ch);")
        indent(file, "}));")
        indent(file, "}")
        file.write("\n")
        indent(file, "// trim from end (in place)")
        indent(file, "static inline void rtrim(std::string &s) {")
        indent(file, "s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) {")
        indent(file, "return !std::isspace(ch);")
        indent(file, "}).base(), s.end());")
        indent(file, "}")
        file.write("\n")
        indent(file, "static std::set<std::string> tokenizer(const char *str_, const char *def_) {")
        indent(file, "const char *def = def_ ? def_ : \"\";")
        indent(file, "std::string str(getenv(str_) ? getenv(str_) : def);")
        indent(file, "std::string delim = \",\";")
        indent(file, "std::set<std::string> tokens;")
        file.write("\n")
        indent(file, "while (auto pos = str.find(\",\")) {")
        indent(file, "std::string newstr = str.substr(0, pos);")
        indent(file, "ltrim(newstr);")
        indent(file, "rtrim(newstr);")
        indent(file, "// Skip empty string")
        indent(file, "if(!newstr.empty()) {")
        indent(file, "if (tokens.find(newstr) != tokens.end()) {")
        indent(file, "// WARN(\"Duplicate token %s found in the value of %s\", newstr.c_str(), str_);")
        indent(file, "}")
        indent(file, "tokens.insert(newstr);")
        indent(file, "}")
        indent(file, "str.erase(0, pos + delim.length());")
        indent(file, "if (pos == std::string::npos) {")
        indent(file, "break;")
        indent(file, "}")
        indent(file, "}")
        indent(file, "return tokens;")
        indent(file, "}")
        file.write("\n")

    def externDecl(self, file):
        indent(file, "extern %s %s;" % (self.type, self.name))
        file.write("\n")

    def storageDecl(self, file):
        indent(file, "%s %s;" % (self.type, self.name))
        file.write("\n")

    def desc(self, file):
        file.write("\n")
        file.write("%s\n" % self.name)
        file.write("Description:\n")
        d = self.description.split("\n")
        for line in d:
            file.write("    %s\n" % line)
        file.write("Type: %s\n" % self.type)
        file.write("Default: %s\n" % self.default)


class bool(basetype):
    @staticmethod
    def utilfns(file):
        indent(file, "static bool env2bool(const char *str_, const char *def) {")
        indent(file, "std::string str(getenv(str_) ? getenv(str_) : def);")
        indent(file, "std::transform(str.cbegin(), str.cend(), str.begin(), " +
               "[](unsigned char c) { return std::tolower(c); });")
        indent(file, "if (str == \"y\") return true;")
        indent(file, "else if (str == \"n\") return false;")
        indent(file, "else if (str == \"yes\") return true;")
        indent(file, "else if (str == \"no\") return false;")
        indent(file, "else if (str == \"t\") return true;")
        indent(file, "else if (str == \"f\") return false;")
        indent(file, "else if (str == \"true\") return true;")
        indent(file, "else if (str == \"false\") return false;")
        indent(file, "else if (str == \"1\") return true;")
        indent(file, "else if (str == \"0\") return false;")
        indent(file, "// else WARN(\"Unrecognized value for env %s\\n\", str_);")
        indent(file, "return true;")
        indent(file, "}")
        file.write("\n")

    def unitTest(self, file):
        for i, val in enumerate(["y", "yes", "true", "1"]):
            indent(file, "TEST_F(CvarTest, %s_value_y%s) {" % (self.name, i))
            indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, val))
            indent(file, "ncclCvarInit();")
            indent(file, "EXPECT_TRUE(%s);" % (self.name))
            indent(file, "}")
            file.write("\n")

        for i, val in enumerate(["n", "no", "false", "0"]):
            indent(file, "TEST_F(CvarTest, %s_value_n%s) {" % (self.name, i))
            indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, val))
            indent(file, "ncclCvarInit();")
            indent(file, "EXPECT_FALSE(%s);" % (self.name))
            indent(file, "}")
            file.write("\n")

        if self.default:
            indent(file, "TEST_F(CvarTest, %s_default_value) {" % (self.name))
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            func = "EXPECT_TRUE" if self.default == "true" else "EXPECT_FALSE"
            indent(file, "%s(%s);" % (func, self.name))
            indent(file, "}")
            file.write("\n")

    def readenv(self, file):
        indent(file, "%s = env2bool(\"%s\", \"%s\");" %
            (self.name, self.name, self.default))
        file.write("\n")


class int(basetype):
    @staticmethod
    def utilfns(file):
        indent(file, "static int env2int(const char *str, const char *def) {")
        indent(file, "return getenv(str) ? atoi(getenv(str)) : atoi(def);")
        indent(file, "}")
        file.write("\n")

    def unitTest(self, file):
        for i, val in enumerate(["-100", "0", "9999", "INT_MAX", "INT_MIN"]):
            indent(file, "TEST_F(CvarTest, %s_value_%s) {" % (self.name, i))
            indent(file, "testIntValue(\"%s\", %s);" % (self.name, val))
            indent(file, "EXPECT_EQ(%s, %s);" % (self.name, val))
            indent(file, "}")
            file.write("\n")

        if self.default:
            indent(file, "TEST_F(CvarTest, %s_default_value) {" % (self.name))
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "EXPECT_EQ(%s, %s);" % (self.name, self.default))
            indent(file, "}")
            file.write("\n")

    def readenv(self, file):
        indent(file, "%s = env2int(\"%s\", \"%s\");" %
            (self.name, self.name, self.default))
        file.write("\n")


class string(basetype):
    @staticmethod
    def utilfns(file):
        indent(file, "static std::string env2str(const char *str, const char *def_) {")
        indent(file, "const char *def = def_ ? def_ : \"\";")
        indent(file, "std::string str_s = getenv(str) ? std::string(getenv(str)) : std::string(def);")
        indent(file, "ltrim(str_s);")
        indent(file, "rtrim(str_s);")
        indent(file, "return str_s;")
        indent(file, "}")
        file.write("\n")

    def externDecl(self, file):
        indent(file, "extern std::string %s;" % self.name)
        file.write("\n")

    def storageDecl(self, file):
        indent(file, "std::string %s;" % self.name)
        file.write("\n")

    def unitTest(self, file):
        for i, val in enumerate(["val1", "  val2_with_space   "]):
            indent(file, "TEST_F(CvarTest, %s_value_%s) {" % (self.name, i))
            indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, val))
            indent(file, "ncclCvarInit();")
            indent(file, "EXPECT_EQ(%s, \"%s\");" % (self.name, val.trim()))
            indent(file, "}")
            file.write("\n")

        if self.default:
            indent(file, "TEST_F(CvarTest, %s_default_value) {" % (self.name))
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "EXPECT_EQ(%s, \"%s\");" % (self.name, self.default))
            indent(file, "}")
            file.write("\n")

    def readenv(self, file):
        if (self.default != None):
            indent(file, "%s = env2str(\"%s\", \"%s\");" %
                (self.name, self.name, self.default))
        else:
            indent(file, "%s = env2str(\"%s\", nullptr);" %
                (self.name, self.name))
        file.write("\n")


class stringlist(basetype):
    @staticmethod
    def utilfns(file):
        indent(file, "static std::set<std::string> env2strlist(const char *str, const char *def) {")
        indent(file, "return tokenizer(str, def);")
        indent(file, "}")
        file.write("\n")

    def externDecl(self, file):
        indent(file, "extern std::set<std::string> %s;" % self.name)
        file.write("\n")

    def storageDecl(self, file):
        indent(file, "std::set<std::string> %s;" % self.name)
        file.write("\n")

    def unitTest(self, file):
        for i, val in enumerate(["val1,val2,val3", "val1:1,val2:2,val3:3", "val", "val1, val_w_space  "]):
            indent(file, "TEST_F(CvarTest, %s_valuelist_%s) {" % (self.name, i))
            indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, val))
            trimedVals = [v.strip() for v in val.split(",")]
            indent(file, "std::vector<std::string> vals{\"%s\"};" % ("\",\"".join(trimedVals)))
            indent(file, "ncclCvarInit();")
            indent(file, "checkListValues<std::string>(vals, %s);" % (self.name))
            indent(file, "}")
            file.write("\n")

        indent(file, "TEST_F(CvarTest, %s_default_value) {" % (self.name))
        if self.default:
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "{")
            indent(file, "std::vector<std::string> vals{\"%s\"};" % (self.default.replace("," , "\",\"")))
            indent(file, "checkListValues<std::string>(vals, %s);" % (self.name))
            indent(file, "}")
        else:
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "EXPECT_EQ(%s.size(), 0);" % (self.name))
        indent(file, "}")
        file.write("\n")

    def readenv(self, file):
        indent(file, "%s.clear();" % self.name)
        if (self.default != None):
            indent(file, "%s = env2strlist(\"%s\", \"%s\");" %
                (self.name, self.name, self.default))
        else:
            indent(file, "%s = env2strlist(\"%s\", nullptr);" %
                (self.name, self.name))
        file.write("\n")


class enum(basetype):
    @staticmethod
    def utilfns(file):
        pass

    def externDecl(self, file):
        choiceList = self.choices.replace(" ", "").split(",")
        indent(file, "enum class %s {" % self.name)
        for c in choiceList:
            indent(file, "%s," % c)
        indent(file, "};")
        indent(file, "extern enum %s %s;" % (self.name, self.name))
        file.write("\n")

    def storageDecl(self, file):
        indent(file, "enum %s %s;" % (self.name, self.name))
        file.write("\n")

    def unitTest(self, file):
        choiceList = self.choices.replace(" ", "").split(",")
        for i, val in enumerate(choiceList):
            indent(file, "TEST_F(CvarTest, %s_single_choice_%s) {" % (self.name, i))
            indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, val))
            indent(file, "ncclCvarInit();")
            indent(file, "EXPECT_EQ(%s, %s::%s);" % (self.name, self.name, val))
            indent(file, "}")
            file.write("\n")

        if self.default:
            indent(file, "TEST_F(CvarTest, %s_default_choice) {" % (self.name))
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "EXPECT_EQ(%s, %s::%s);" % (self.name, self.name, self.default))
            indent(file, "}")
        file.write("\n")

    def readenv(self, file):
        indent(file, "if (getenv(\"%s\") == nullptr) {" % self.name)
        indent(file, "%s = %s::%s;" % (self.name, self.name, self.default))
        indent(file, "} else {")
        indent(file, "std::string str(getenv(\"%s\"));" % self.name)
        choices = self.choices.replace(" ", "").split(",")
        for idx, c in enumerate(choices):
            if (idx == 0):
               indent(file, "if (str == std::string(\"%s\")) {" % c)
            else:
               indent(file, "} else if (str == std::string(\"%s\")) {" % c)
            indent(file, "%s = %s::%s;" % (self.name, self.name, c))
        indent(file, "} else {")
        indent(file, "// WARN(\"Unknown value %%s for env %s\", str.c_str());" % self.name)
        indent(file, "}")
        indent(file, "}")
        file.write("\n")


class enumlist(basetype):
    @staticmethod
    def utilfns(file):
        pass

    def externDecl(self, file):
        choiceList = self.choices.replace(" ", "").split(",")
        indent(file, "enum class %s {" % self.name)
        for c in choiceList:
            indent(file, "%s," % c)
        indent(file, "};")
        indent(file, "extern std::set<enum %s> %s;" % (self.name, self.name))
        file.write("\n")

    def storageDecl(self, file):
        indent(file, "std::set<enum %s> %s;" % (self.name, self.name))
        file.write("\n")

    def unitTest(self, file):
        choiceList = self.choices.replace(" ", "").split(",")
        allChoicesEnum = ["%s::%s" % (self.name, c) for c in choiceList]

        for i, val in enumerate(choiceList):
            indent(file, "TEST_F(CvarTest, %s_single_choice_%s) {" % (self.name, i))
            indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, val))
            indent(file, "ncclCvarInit();")
            indent(file, "std::vector<enum %s> vals{%s::%s};" % (self.name, self.name, val))
            indent(file, "checkListValues<enum %s>(vals, %s);" % (self.name, self.name))
            indent(file, "}")
            file.write("\n")

        indent(file, "TEST_F(CvarTest, %s_all_choices) {" % (self.name))
        indent(file, "setenv(\"%s\", \"%s\", 1);" % (self.name, self.choices))
        indent(file, "ncclCvarInit();")
        indent(file, "std::vector<enum %s> vals{%s};" % (self.name, ",".join(allChoicesEnum)))
        indent(file, "checkListValues<enum %s>(vals, %s);" % (self.name, self.name))
        indent(file, "}")
        file.write("\n")

        defaultChoicesEnum = ["%s::%s" % (self.name, c) for c in self.default.replace(" ", "").split(",")]
        indent(file, "TEST_F(CvarTest, %s_default_choices) {" % (self.name))
        if defaultChoicesEnum:
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "std::vector<enum %s> vals{%s};" % (self.name, ",".join(defaultChoicesEnum)))
            indent(file, "checkListValues<enum %s>(vals, %s);" % (self.name, self.name))
        else:
            indent(file, "testDefaultValue(\"%s\");" % (self.name))
            indent(file, "EXPECT_EQ(%s.size(), 0);" % (self.name))
        indent(file, "}")
        file.write("\n")

    def readenv(self, file):
        indent(file, "{")
        indent(file, "%s.clear();" % self.name)
        indent(file, "auto tokens = tokenizer(\"%s\", \"%s\");" % (self.name, self.default))
        choices = self.choices.replace(" ", "").split(",")
        indent(file, "for (auto token : tokens) {")
        for idx, c in enumerate(choices):
            if (idx == 0):
               indent(file, "if (token == std::string(\"%s\")) {" % c)
            else:
               indent(file, "} else if (token == std::string(\"%s\")) {" % c)
            indent(file, "%s.insert(%s::%s);" % (self.name, self.name, c))
        indent(file, "} else {")
        indent(file, "// WARN(\"Unknown value %%s for env %s\", token.c_str());" % self.name)
        indent(file, "}")
        indent(file, "}")
        indent(file, "}")
        file.write("\n")


def populateCCFile(allcvars, filename):
    file = open(filename, "w")
    file.write("// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.\n")
    file.write("\n")
    file.write("// Automatically generated\n")
    file.write("//   by ./maint/extractcvars.py\n")
    file.write("// DO NOT EDIT!!!\n")
    file.write("\n")
    file.write("#include <string>\n")
    file.write("#include <iostream>\n")
    file.write("#include <algorithm>\n")
    file.write("#include <unordered_set>\n")
    file.write("#include <set>\n")
    file.write("#include <cstring>\n")
    file.write("#include \"nccl_cvars.h\"\n")
    file.write("#include \"debug.h\"\n")
    file.write("\n")

    basetype.utilfns(file)
    bool.utilfns(file)
    int.utilfns(file)
    string.utilfns(file)
    stringlist.utilfns(file)
    enum.utilfns(file)
    enumlist.utilfns(file)

    for cvar in allcvars:
        cvar.storageDecl(file)

    indent(file, "extern char **environ;")
    file.write("\n")

    indent(file, "void ncclCvarInit() {")
    indent(file, "std::unordered_set<std::string> env;")
    for cvar in allcvars:
        indent(file, "env.insert(\"%s\");" % cvar.name)
    for e in acceptedEnvs:
        indent(file, "env.insert(\"%s\");" % e)

    file.write("\n")
    indent(file, "char **s = environ;")
    indent(file, "for (; *s; s++) {")
    indent(file, "if (!strncmp(*s, \"NCCL_\", strlen(\"NCCL_\"))) {")
    indent(file, "std::string str(*s);")
    indent(file, "str = str.substr(0, str.find(\"=\"));")
    indent(file, "if (env.find(str) == env.end()) {")
    indent(file, "// WARN(\"Unknown env %s in the NCCL namespace\\n\", str.c_str());")
    indent(file, "}")
    indent(file, "}")
    indent(file, "}")
    file.write("\n")

    for cvar in allcvars:
        cvar.readenv(file)

    indent(file, "}")
    file.close()


def populateHFile(allcvars, filename):
    file = open(filename, "w")
    file.write("// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.\n")
    file.write("\n")
    file.write("// Automatically generated\n")
    file.write("//   by ./maint/extractcvars.py\n")
    file.write("// DO NOT EDIT!!!\n")
    file.write("\n")
    file.write("#ifndef NCCL_CVARS_H_INCLUDED\n")
    file.write("#define NCCL_CVARS_H_INCLUDED\n")
    file.write("\n")
    file.write("#include <string>\n")
    file.write("#include <set>\n")
    file.write("\n")

    for cvar in allcvars:
        cvar.externDecl(file)

    indent(file, "void ncclCvarInit();")
    file.write("\n")

    file.write("#endif  /* NCCL_CVARS_H_INCLUDED */\n")
    file.close()


def populateReadme(allcvars, filename):
    file = open(filename, "w")
    file.write("(c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.\n")
    file.write("\n")
    file.write("Automatically generated\n")
    file.write("  by ./maint/extractcvars.py\n")
    file.write("DO NOT EDIT!!!\n")
    for cvar in allcvars:
        cvar.desc(file)
    file.close()

def populateUT(allcvars, templateFilename, outputFilename):
    file = StringIO()

    # Generate unit test declarations
    file.write("// Automatically generated by ./maint/extractcvars.py\n")
    file.write("// DO NOT EDIT!!!\n")
    for cvar in allcvars:
        cvar.unitTest(file)
    utDecl = file.getvalue()

    # Load template and insert generated contents
    with open(templateFilename, "r") as tpl:
        fileContents = tpl.read()
        fileContents = fileContents.replace("## NCCL_CVAR_TESTS_DECL ##", utDecl)

        with open(outputFilename, "w") as out:
            out.write(fileContents)
    file.close()

def main():
    filenames = []
    for (root, dirs, files) in os.walk('.', topdown=True):
        for x in files:
            if x.endswith(".cc") or x.endswith(".h"):
                filenames.append(os.path.join(root, x))

    data = loadCvarsFromFiles(filenames)
    if (data['cvars'] == None):
        return

    allcvars = []
    for cvar in data['cvars']:
        if (cvar['type'] == "bool"):
            allcvars.append(bool(cvar))
        elif (cvar['type'] == "int"):
            allcvars.append(int(cvar))
        elif (cvar['type'] == "string"):
            allcvars.append(string(cvar))
        elif (cvar['type'] == "stringlist"):
            allcvars.append(stringlist(cvar))
        elif (cvar['type'] == "enum"):
            allcvars.append(enum(cvar))
        elif (cvar['type'] == "enumlist"):
            allcvars.append(enumlist(cvar))
        else:
            print("UNKNOWN TYPE: %s" % cvar['type'])
            exit()

    populateCCFile(allcvars, "src/misc/nccl_cvars.cc")
    populateHFile(allcvars, "src/include/nccl_cvars.h")
    populateReadme(allcvars, "README.cvars")
    populateUT(allcvars, "src/tests/CvarUT.cc.in", "src/tests/CvarUT.cc")


if __name__ == "__main__":
    main()

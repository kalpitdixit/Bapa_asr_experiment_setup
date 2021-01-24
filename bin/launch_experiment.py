from constants import ESPNET_DIR
import uuid


BAPA_PROTO = os.path.join(ESPNET_DIR, "egs/Bapa_proto")
    


def get_exp_id(dname):
    while True:
        uid = str(uuid.uuid4())[:8]
        exp_dname = os.path.join(ESPNET_DIR, "egs", "Bapa_{}".format(uid))
        if not os.path.exists(exp_dname):
            break
    return dname
            


if __name__=="__main__":
    ##### #####

    ##### CREATE EXP DIR #####
    exp_dname = get_exp_id(os.path.join(ESPNET_DIR, "egs"))
    os.system("cp -r {} {}".format(BAPA_PROTO, exp_dname))
